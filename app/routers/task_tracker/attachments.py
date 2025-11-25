import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.attachment import AttachmentCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import (
    AssetPermissions,
    AuthorizedUser,
    DiligencePermissions,
    OnMPermissions,
    get_authorized_attachment,
    get_authorized_task,
)
from app.helpers.files.file_handler import TaskAttachmentHandler
from app.models.attachment import Attachment
from app.models.task import Task
from app.schema.attachment import AttachmentsList, CreateAttachmentSchema
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
attachments_router = APIRouter()


@attachments_router.post(
    "/upload-url",
    response_model=FileUploadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(get_authorized_task),
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit),
                    DiligencePermissions(PermissionsActions.edit),
                    OnMPermissions(PermissionsActions.edit),
                ]
            )
        ),
    ],
)
async def get_attachment_upload_presigned_url(
    board_id: int,
    task_id: int,
    file_data: FileNameSchema,
):
    file_extension = file_data.filename.split(".")[-1]
    file_handler = TaskAttachmentHandler()
    filepath = file_handler.generate_gcs_attachment_filepath(board_id, task_id, file_data.filename)
    return {"filepath": filepath, "upload_url": file_handler.generate_signed_url_for_upload(filepath, file_extension)}


@attachments_router.post(
    "/track-uploaded-attachment",
    response_model=FileUploadSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(get_authorized_task),
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit),
                    DiligencePermissions(PermissionsActions.edit),
                    OnMPermissions(PermissionsActions.edit),
                ]
            )
        ),
    ],
)
async def track_uploaded_attachment(
    task_id: int,
    file_data: CreateAttachmentSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    file_payload = file_data.model_dump()
    file_payload["task_id"] = task_id
    file_payload["user_id"] = current_user.id
    AttachmentCRUD(db_session).create_item(file_payload)
    return {"code": status.HTTP_200_OK, "message": "File successfully uploaded"}


@attachments_router.get(
    "/",
    response_model=AttachmentsList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.view),
                    DiligencePermissions(PermissionsActions.view),
                    OnMPermissions(PermissionsActions.view),
                ]
            )
        )
    ],
)
async def get_attachments_list(
    task: Task = Depends(get_authorized_task),
    db_session: Session = Depends(get_session),
):
    return {"items": AttachmentCRUD(db_session).get_task_attachments(task.id)}


@attachments_router.get(
    "/{attachment_id}",
    response_model=FileDownloadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.view),
                    DiligencePermissions(PermissionsActions.view),
                    OnMPermissions(PermissionsActions.view),
                ]
            )
        )
    ],
)
async def get_download_url(
    attachment: Attachment = Depends(get_authorized_attachment),
):
    return {
        "download_url": TaskAttachmentHandler().generate_download_signed_url(attachment.filepath, attachment.filename)
    }


@attachments_router.delete(
    "/{attachment_id}",
    response_model=FileRemovalSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Delete attachment completely from DB and GCS",
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit),
                    DiligencePermissions(PermissionsActions.edit),
                    OnMPermissions(PermissionsActions.edit),
                ]
            )
        )
    ],
)
async def remove_attachment(
    attachment_id: int,
    db_session: Session = Depends(get_session),
    attachment: Attachment = Depends(get_authorized_attachment),
):
    # first, remove attachment file from GCS
    error = TaskAttachmentHandler().delete_file(attachment.filepath)
    if error:
        raise HTTPException(error["code"], error["message"])
    # then remove record from DB
    AttachmentCRUD(db_session).delete_by_id(attachment_id)
    return {"code": status.HTTP_200_OK, "message": "File has been successfully deleted"}


@attachments_router.get(
    "/{attachment_id}/file-preview-url/",
    response_model=FilePreviewURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get file preview url for pdf, jpeg, png files",
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.view),
                    DiligencePermissions(PermissionsActions.view),
                    OnMPermissions(PermissionsActions.view),
                ]
            )
        )
    ],
)
async def attachment_view_url(
    attachment: Attachment = Depends(get_authorized_attachment),
):
    return {
        "preview_url": TaskAttachmentHandler().generate_file_view_signed_url(attachment.filepath, attachment.filename)
    }
