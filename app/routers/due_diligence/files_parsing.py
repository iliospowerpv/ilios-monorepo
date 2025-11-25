import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.crud.commented_entity import CommentedEntityCRUD
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser, DiligencePermissions
from app.helpers.authorization.project_access import get_authorized_file
from app.helpers.cloud_function_client import FileParseFuncHTTPClient
from app.helpers.configs.agreement_names_helper import AgreementNamesMappingHandler
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.files.file_helper import combine_user_ai_parsing_results
from app.models.comment import CommentedEntityTypeEnum
from app.models.file import File as FileModel
from app.models.file import FileParsingStatuses
from app.schema.file import FileKeysList, FileParseTriggerSuccess, FileParsingStatus
from app.settings import settings
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, HTTP_409_RESPONSE, FileMessages, PermissionsActions

logger = logging.getLogger(__name__)
files_parsing_router = APIRouter()


@files_parsing_router.post(
    "/parsing/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=FileParseTriggerSuccess,
    responses={
        **HTTP_403_RESPONSE,
        **HTTP_404_RESPONSE,
        **HTTP_409_RESPONSE(message=FileMessages.file_parse_conflict),
    },
    description="Trigger GCP Cloud Function to start AI file parsing asynchronously without waiting success response",
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.edit)))],
)
async def trigger_file_parsing(
    file: FileModel = Depends(get_authorized_file), db_session: Session = Depends(get_session)
):
    if file.document.name.value not in AIParsingHandler(db_session).get_parsable_documents_list():
        logger.warning(message := f"Parsing feature is not available for the <{file.document.name.value}> files")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    pipeline_document_name = AgreementNamesMappingHandler(db_session).get_pipeline_agreement_name(file.document.name)
    if not pipeline_document_name:
        logger.warning(message := f"Parsing config is not found for the <{file.document.name.value}> files")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    file_extension = file.filename.split(".")[-1]
    if file_extension not in settings.ai_parsing_allowed_extensions.split(","):
        message = (
            f"Parsing feature is not available for the <{file_extension}> file type. "
            f"Allowed file types: <{settings.ai_parsing_allowed_extensions}>"
        )
        logger.warning(message)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=message)

    ai_results_crud = AIParsingResultCRUD(db_session)
    if file.latest_ai_result and file.latest_ai_result.status == FileParsingStatuses.processing:
        logger.warning(f"There is already parse processing started for file {file.id}")
        raise HTTPException(status.HTTP_409_CONFLICT, detail=FileMessages.file_parse_conflict)

    new_ai_record = ai_results_crud.create_item(
        {"file_id": file.id, "status": FileParsingStatuses.not_started, "start_time": datetime.now(timezone.utc)}
    )
    # wrap into try-except block to ensure ai_result_record item has proper status even if CF invocation failed
    try:
        file_parse_func_client = FileParseFuncHTTPClient()
        payload_for_trigger = file_parse_func_client.prepare_trigger_payload(
            file, new_ai_record.id, pipeline_document_name
        )

        response = file_parse_func_client.post(payload_for_trigger)
        if not response.ok:
            logger.warning(
                f"Parsing for file {file.id} was unable to start due to the error response from Cloud Function: "
                f"{response.status_code}, {response.reason}"
            )
            raise HTTPException(response.status_code, detail=response.reason)
    except Exception as exc:
        ai_results_crud.update_by_id(
            new_ai_record.id,
            {"status": FileParsingStatuses.processing_start_failed, "end_time": datetime.now(timezone.utc)},
        )
        logger.warning(f"Parsing for file {file.id} was unable to start due to the error: {str(exc)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"An error occurred during file AI processing: {str(exc)}")

    ai_results_crud.update_by_id(new_ai_record.id, {"status": FileParsingStatuses.processing})
    return {"code": status.HTTP_202_ACCEPTED, "message": FileMessages.file_parse_trigger_success}


@files_parsing_router.get(
    "/parsing-status/",
    response_model=FileParsingStatus,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get actual at the moment file parsing status",
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.view)))],
)
async def file_parsing_status(
    file: File = Depends(get_authorized_file),
):
    return file.latest_ai_result if file.latest_ai_result else {}


@files_parsing_router.get(
    "/parsing-result/",
    response_model=FileKeysList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get list of file keys with custom User values and values received from AI",
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.view)))],
)
async def get_file_parsing_results(
    file: File = Depends(get_authorized_file), db_session: Session = Depends(get_session)
):
    response = combine_user_ai_parsing_results(document=file.document, due_diligence_file=file, db_session=db_session)
    # post-process to retrieve comments and related to the result key,
    # DB relationship usage on each entity will decrease the performance,
    # let's retrieve all comments and then attach to the corresponding key object
    keys_ids = [res["id"] for res in response if res["id"]]
    keys_comments = CommentedEntityCRUD(db_session).get_by_entities_grouped(
        entity_type=CommentedEntityTypeEnum.document_key, entities_ids=keys_ids
    )
    for comments_row in keys_comments:
        document_id, comments = comments_row
        document = [document_response for document_response in response if document_response["id"] == document_id][0]
        document["comments"] = comments
    return {"keys": response}
