import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, status
from sqlalchemy.orm import Session

from app.crud.file import FileCRUD
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser, DiligencePermissions
from app.helpers.authorization.project_access import get_authorized_document, get_authorized_file
from app.helpers.chatbot.files_sync import ChatBotFilesSyncer
from app.helpers.configs.agreement_names_helper import AgreementNamesMappingHandler
from app.helpers.files.file_handler import DueDiligenceFileHandler
from app.models.document import Document
from app.models.file import File as FileModel
from app.schema.file import (
    CreateFileSchema,
    FileDownloadURLSchema,
    FileIsActual,
    FileNameSchema,
    FilePreviewURLSchema,
    FileRemovalSuccess,
    FilesList,
    FileUpdateIsActualSuccess,
    FileUploadSuccess,
    FileUploadURLSchema,
)
from app.schema.user import CurrentUserSchema
from app.settings import settings
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, FileMessages, PermissionsActions

logger = logging.getLogger(__name__)
files_router = APIRouter()


@files_router.get(
    "/",
    response_model=FilesList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.view)))],
)
async def get_files_list(
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    return {"items": FileCRUD(db_session).get_document_files(document.id)}


@files_router.delete(
    "/{file_id}",
    response_model=FileRemovalSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Soft delete file (setting `deleted` flag to True)",
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.edit)))],
)
async def remove_file(
    background_tasks: BackgroundTasks,
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    FileCRUD(db_session).update_by_id(file.id, {"deleted": True})
    # send AI trigger to untrack the file from the ChatBot storage
    ai_params = {"file_id": file.id}
    background_tasks.add_task(ChatBotFilesSyncer().delete_file, ai_params)
    return {"code": status.HTTP_200_OK, "message": "File has been successfully deleted"}


@files_router.get(
    "/{file_id}",
    response_model=FileDownloadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.view)))],
)
async def get_download_url(
    file: File = Depends(get_authorized_file),
):
    return {"download_url": DueDiligenceFileHandler().generate_download_signed_url(file.filepath, file.filename)}


@files_router.post(
    "/upload-url/",
    response_model=FileUploadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.edit)))],
)
async def get_upload_url(
    site_id: int,
    document_id: int,
    file_data: FileNameSchema,
    document: Document = Depends(get_authorized_document),
):
    file_extension = file_data.filename.split(".")[-1]
    file_handler = DueDiligenceFileHandler()
    filepath = file_handler.generate_due_diligence_gcs_filepath(
        document.site.company_id, site_id, document_id, file_data.filename
    )
    return {"filepath": filepath, "upload_url": file_handler.generate_signed_url_for_upload(filepath, file_extension)}


@files_router.post(
    "/track-uploaded-file/",
    response_model=FileUploadSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Create a file record with uploaded file details",
)
async def create_uploaded_file(
    document_id: int,
    file_data: CreateFileSchema,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.edit)))],
    background_tasks: BackgroundTasks,
    document: Document = Depends(get_authorized_document),  # noqa: U100
    db_session: Session = Depends(get_session),
):
    file_payload = file_data.model_dump()
    file_payload["document_id"] = document_id
    file_payload["user_id"] = current_user.id
    new_file = FileCRUD(db_session).create_item(file_payload)
    # use pipeline document name if it used in AI, otherwise return 'Other' literal
    agreement_name = AgreementNamesMappingHandler(db_session).get_pipeline_agreement_name(document.name)
    if not agreement_name:
        agreement_name = "Other"
    # define nesting level of the document
    section_name = document.section.name.value
    subsection_name = None
    # move section name deeper if it's the subsection
    if document.section.parent_section:
        section_name = document.section.parent_section.name.value
        subsection_name = document.section.name.value
    ai_payload = {
        "file_link": f"gs://{settings.due_diligence_gcs_bucket}/{file_data.filepath}",
        "file_id": new_file.id,
        "site_name": document.site.name,
        "site_id": document.site_id,
        "company_name": document.site.company.name,
        "company_id": document.site.company_id,
        "agreement_name": agreement_name,
        "document_name": document.name.value,
        "file_name": file_data.filename,
        "section_name": section_name,
        "subsection_name": subsection_name,
    }
    background_tasks.add_task(ChatBotFilesSyncer().upload_file, ai_payload)
    return {"code": status.HTTP_200_OK, "message": "File successfully uploaded"}


@files_router.get(
    "/{file_id}/file-preview-url/",
    response_model=FilePreviewURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get file preview url for pdf, jpeg, png files",
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.view)))],
)
async def file_view_url(
    file: File = Depends(get_authorized_file),
):
    return {"preview_url": DueDiligenceFileHandler().generate_file_view_signed_url(file.filepath, file.filename)}


@files_router.put(
    "/{file_id}/file-is-actual/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=FileUpdateIsActualSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.edit)))],
)
async def update_is_actual_file_status(
    is_actual_payload: FileIsActual,
    background_tasks: BackgroundTasks,
    file: File = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    FileCRUD(db_session).update_by_id(file.id, is_actual_payload.model_dump())
    # send AI trigger
    ai_params = {"actual": str(is_actual_payload.is_actual).lower(), "file_id": file.id}
    background_tasks.add_task(ChatBotFilesSyncer().mark_file_actual, ai_params)
    return {"code": status.HTTP_200_OK, "message": FileMessages.file_actual_status_updated}
