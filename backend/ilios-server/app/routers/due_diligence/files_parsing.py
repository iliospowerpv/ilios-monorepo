import logging
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.crud.commented_entity import CommentedEntityCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_file
from app.helpers.permission_guards import require_module_permission
from app.helpers.cloud_function_client import FileParseFuncHTTPClient
from app.helpers.configs.agreement_names_helper import AgreementNamesMappingHandler
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.files.file_helper import combine_user_ai_parsing_results
from app.models.comment import CommentedEntityTypeEnum
from app.models.file import File as FileModel
from app.models.file import FileParsingStatuses, AIParsingResult
from app.schema.file import FileKeysList, FileParseTriggerSuccess, FileParsingStatus
from app.schema.user import CurrentUserSchema
from app.services.extraction_pipeline_service import ExtractionPipelineService
from app.settings import settings
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, HTTP_409_RESPONSE, FileMessages

logger = logging.getLogger(__name__)
files_parsing_router = APIRouter()


class ReprocessRequest(BaseModel):
    schema_version_id: Optional[int] = None
    prompt_template_id: Optional[int] = None
    force: bool = False

    class Config:
        from_attributes = True


class ReprocessResponse(BaseModel):
    job_id: int
    status: str
    message: str
    is_reprocess: bool
    schema_version_id: Optional[int] = None
    prompt_template_id: Optional[int] = None


class EvidenceSchema(BaseModel):
    page: Optional[int] = None
    snippet: Optional[str] = None
    anchor_text: Optional[str] = None

    class Config:
        from_attributes = True


class ParseRunSchema(BaseModel):
    id: int
    file_id: int
    status: str
    extraction_run_number: Optional[int] = None
    document_type_id: Optional[int] = None
    schema_version_id: Optional[int] = None
    prompt_template_id: Optional[int] = None
    is_reprocess: Optional[bool] = False
    force_reprocess: Optional[bool] = False
    retries: Optional[int] = 0
    error_message: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ParseRunHistoryResponse(BaseModel):
    file_id: int
    runs: list[ParseRunSchema]
    total: int


@files_parsing_router.get(
    "/runs/",
    response_model=ParseRunHistoryResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get parse run history for a file, including status, bindings, and retries.",
)
async def get_parse_run_history(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    ai_results_crud = AIParsingResultCRUD(db_session)
    runs = ai_results_crud.get_runs_for_file(file.id)

    run_schemas = []
    for run in runs:
        run_schemas.append(ParseRunSchema(
            id=run.id,
            file_id=run.file_id,
            status=run.status.value if run.status else "unknown",
            extraction_run_number=run.extraction_run_number,
            document_type_id=run.document_type_id,
            schema_version_id=run.schema_version_id,
            prompt_template_id=run.prompt_template_id,
            is_reprocess=run.is_reprocess,
            force_reprocess=run.force_reprocess,
            retries=run.retries,
            error_message=run.error_message,
            start_time=run.start_time.isoformat() if run.start_time else None,
            end_time=run.end_time.isoformat() if run.end_time else None,
            created_at=run.created_at.isoformat() if hasattr(run, 'created_at') and run.created_at else None,
        ))

    return ParseRunHistoryResponse(
        file_id=file.id,
        runs=run_schemas,
        total=len(run_schemas),
    )


@files_parsing_router.get(
    "/runs/{run_id}/",
    response_model=ParseRunSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get details of a specific parse run.",
)
async def get_parse_run_detail(
    run_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    ai_results_crud = AIParsingResultCRUD(db_session)
    run = ai_results_crud.get_run_by_id(run_id)

    if not run or run.file_id != file.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Parse run not found")

    return ParseRunSchema(
        id=run.id,
        file_id=run.file_id,
        status=run.status.value if run.status else "unknown",
        extraction_run_number=run.extraction_run_number,
        document_type_id=run.document_type_id,
        schema_version_id=run.schema_version_id,
        prompt_template_id=run.prompt_template_id,
        is_reprocess=run.is_reprocess,
        force_reprocess=run.force_reprocess,
        retries=run.retries,
        error_message=run.error_message,
        start_time=run.start_time.isoformat() if run.start_time else None,
        end_time=run.end_time.isoformat() if run.end_time else None,
        created_at=run.created_at.isoformat() if hasattr(run, 'created_at') and run.created_at else None,
    )


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
)
async def trigger_file_parsing(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
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
)
async def file_parsing_status(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
    return file.latest_ai_result if file.latest_ai_result else {}


@files_parsing_router.get(
    "/parsing-result/",
    response_model=FileKeysList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get list of file keys with custom User values and values received from AI",
)
async def get_file_parsing_results(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
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


@files_parsing_router.post(
    "/reprocess/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ReprocessResponse,
    responses={
        **HTTP_403_RESPONSE,
        **HTTP_404_RESPONSE,
        **HTTP_409_RESPONSE(message="Reprocess with same bindings already completed"),
    },
    description="Reprocess a file with optional schema/prompt version selection. Creates new parsing job.",
)
async def reprocess_file(
    request: ReprocessRequest,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )

    pipeline_service = ExtractionPipelineService(db_session)
    ai_results_crud = AIParsingResultCRUD(db_session)

    doc_type_name = file.document.name.value
    extraction_config = pipeline_service.get_extraction_config(doc_type_name)
    if not extraction_config:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Document type '{doc_type_name}' not found in registry"
        )

    doc_type_id = extraction_config["document_type"]["id"]
    schema_version_id = request.schema_version_id or extraction_config["schema_version"]["id"]
    prompt_template_id = request.prompt_template_id or extraction_config["prompt_template"]["id"]

    existing_runs = db_session.query(AIParsingResult).filter(
        AIParsingResult.file_id == file.id,
        AIParsingResult.schema_version_id == schema_version_id,
        AIParsingResult.prompt_template_id == prompt_template_id,
        AIParsingResult.status == FileParsingStatuses.completed,
    ).all()

    if existing_runs and not request.force:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Reprocess with same bindings already completed. Use force=true to override."
        )

    run_count = db_session.query(AIParsingResult).filter(
        AIParsingResult.file_id == file.id
    ).count()

    new_job = ai_results_crud.create_item({
        "file_id": file.id,
        "status": FileParsingStatuses.not_started,
        "start_time": datetime.now(timezone.utc),
        "document_type_id": doc_type_id,
        "schema_version_id": schema_version_id,
        "prompt_template_id": prompt_template_id,
        "extraction_run_number": run_count + 1,
        "is_reprocess": True,
        "force_reprocess": request.force,
    })

    pipeline_document_name = AgreementNamesMappingHandler(db_session).get_pipeline_agreement_name(file.document.name)
    if not pipeline_document_name:
        ai_results_crud.update_by_id(new_job.id, {
            "status": FileParsingStatuses.processing_start_failed,
            "error_message": f"Pipeline config not found for {doc_type_name}",
            "end_time": datetime.now(timezone.utc),
        })
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Pipeline config not found for {doc_type_name}")

    try:
        file_parse_func_client = FileParseFuncHTTPClient()
        payload = file_parse_func_client.prepare_trigger_payload(file, new_job.id, pipeline_document_name)
        response = file_parse_func_client.post(payload)
        if not response.ok:
            ai_results_crud.update_by_id(new_job.id, {
                "status": FileParsingStatuses.processing_start_failed,
                "error_message": f"Cloud Function error: {response.status_code}",
                "end_time": datetime.now(timezone.utc),
            })
            raise HTTPException(response.status_code, detail=response.reason)
    except HTTPException:
        raise
    except Exception as exc:
        ai_results_crud.update_by_id(new_job.id, {
            "status": FileParsingStatuses.processing_start_failed,
            "error_message": str(exc),
            "end_time": datetime.now(timezone.utc),
        })
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f"Reprocess failed: {str(exc)}")

    ai_results_crud.update_by_id(new_job.id, {"status": FileParsingStatuses.processing})

    return ReprocessResponse(
        job_id=new_job.id,
        status="processing",
        message="Reprocess job created successfully",
        is_reprocess=True,
        schema_version_id=schema_version_id,
        prompt_template_id=prompt_template_id,
    )
