import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.device_document import DeviceDocumentCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import AssetPermissions, AuthorizedUser
from app.helpers.authorization.project_access import get_authorized_device, get_authorized_device_document
from app.helpers.files.file_handler import DeviceDocumentFileHandler
from app.models.device_document import DeviceDocument
from app.schema.device_document import CreateDocumentSchema
from app.schema.file import (
    FileDownloadURLSchema,
    FileNameSchema,
    FilePreviewURLSchema,
    FileRemovalSuccess,
    FileUploadSuccess,
    FileUploadURLSchema,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions

logger = logging.getLogger(__name__)
device_documents_router = APIRouter()


@device_documents_router.post(
    "/upload-url",
    response_model=FileUploadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(get_authorized_device), Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def get_document_upload_signed_url(
    site_id: int,
    device_id: int,
    file_data: FileNameSchema,
):
    file_extension = file_data.filename.split(".")[-1]
    file_handler = DeviceDocumentFileHandler()
    filepath = file_handler.generate_device_document_gcs_filepath(site_id, device_id, file_data.filename)
    return {"filepath": filepath, "upload_url": file_handler.generate_signed_url_for_upload(filepath, file_extension)}


@device_documents_router.get(
    "/{document_id}/download-url",
    response_model=FileDownloadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_download_url(
    device_document: DeviceDocument = Depends(get_authorized_device_document),
):
    return {
        "download_url": DeviceDocumentFileHandler().generate_download_signed_url(
            device_document.filepath, device_document.filename
        )
    }


@device_documents_router.delete(
    "/{document_id}",
    response_model=FileRemovalSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Delete device document completely from DB and GCS",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def remove_device_document(
    document_id: int,
    db_session: Session = Depends(get_session),
    device_document: DeviceDocument = Depends(get_authorized_device_document),
):
    # first, remove device_document file from GCS
    error = DeviceDocumentFileHandler().delete_file(device_document.filepath)
    if error:
        raise HTTPException(error["code"], error["message"])
    # then remove record from DB
    DeviceDocumentCRUD(db_session).delete_by_id(document_id)
    return {"code": status.HTTP_200_OK, "message": "File has been successfully deleted"}


@device_documents_router.post(
    "/track-uploaded-document",
    response_model=FileUploadSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(get_authorized_device), Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def track_uploaded_document(
    device_id: int,
    document_data: CreateDocumentSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    file_payload = document_data.model_dump()
    file_payload["device_id"] = device_id
    file_payload["user_id"] = current_user.id
    DeviceDocumentCRUD(db_session).create_item(file_payload)
    return {"code": status.HTTP_200_OK, "message": "File successfully uploaded"}


@device_documents_router.get(
    "/{document_id}/file-preview-url/",
    response_model=FilePreviewURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get file preview url for pdf, jpeg, png files",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def document_view_url(
    device_document: DeviceDocument = Depends(get_authorized_device_document),
):
    return {
        "preview_url": DeviceDocumentFileHandler().generate_file_view_signed_url(
            device_document.filepath, device_document.filename
        )
    }
