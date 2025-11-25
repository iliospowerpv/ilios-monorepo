"""Common URLs for site visits <site conditiona> and site visits <field discovery> pictures"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.sv_uploads import SiteVisitUploadCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import (
    AuthorizedUser,
    OnMPermissions,
    get_authorized_site_visit,
    get_authorized_site_visit_upload,
    get_authorized_task,
)
from app.helpers.files.file_handler import SiteVisitFileHandler
from app.helpers.site_visits_uploads_helper import get_sv_upload_section
from app.models.attachment import Attachment
from app.models.site_visit import SiteVisit
from app.schema.attachment import AttachmentsList
from app.schema.file import (
    CreateImageFileSchema,
    FileDownloadURLSchema,
    FilePreviewURLSchema,
    FileRemovalSuccess,
    FileUploadSuccess,
    FileUploadURLSchema,
    ImageFileNameSchema,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions
from app.static.site_visits import SiteVisitsUploads

logger = logging.getLogger(__name__)
sv_uploads_router = APIRouter()


@sv_uploads_router.post(
    f"/{SiteVisitsUploads.site_conditions}/upload-url",
    response_model=FileUploadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(get_authorized_task),
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.edit))),
    ],
)
@sv_uploads_router.post(
    f"/{SiteVisitsUploads.field_discovery}/upload-url",
    response_model=FileUploadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.edit))),
    ],
)
async def get_upload_presigned_url(
    file_data: ImageFileNameSchema,
    site_visit: SiteVisit = Depends(get_authorized_site_visit),
    upload_section: SiteVisitsUploads = Depends(get_sv_upload_section),
):
    file_extension = file_data.filename.split(".")[-1]
    file_handler = SiteVisitFileHandler()
    filepath = file_handler.generate_site_visit_upload_gcs_filepath(
        site_visit.id, file_data.filename, upload_section.value
    )
    return {"filepath": filepath, "upload_url": file_handler.generate_signed_url_for_upload(filepath, file_extension)}


@sv_uploads_router.post(
    f"/{SiteVisitsUploads.site_conditions}/track-uploaded-attachment",
    response_model=FileUploadSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(get_authorized_task),
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.edit))),
    ],
)
@sv_uploads_router.post(
    f"/{SiteVisitsUploads.field_discovery}/track-uploaded-attachment",
    response_model=FileUploadSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.edit))),
    ],
)
async def track_uploaded_item(
    file_data: CreateImageFileSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site_visit: SiteVisit = Depends(get_authorized_site_visit),
    db_session: Session = Depends(get_session),
    upload_section: SiteVisitsUploads = Depends(get_sv_upload_section),
):
    file_payload = file_data.model_dump()
    file_payload.update(
        {
            "site_visit_id": site_visit.id,
            "user_id": current_user.id,
            "section_name": upload_section.value,
        }
    )
    SiteVisitUploadCRUD(db_session).create_item(file_payload)
    return {"code": status.HTTP_200_OK, "message": "File successfully uploaded"}


@sv_uploads_router.get(
    f"/{SiteVisitsUploads.site_conditions}",
    response_model=AttachmentsList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view))),
    ],
)
@sv_uploads_router.get(
    f"/{SiteVisitsUploads.field_discovery}",
    response_model=AttachmentsList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view))),
    ],
)
async def get_uploads_list(
    site_visit: SiteVisit = Depends(get_authorized_site_visit),
    db_session: Session = Depends(get_session),
    upload_section: SiteVisitsUploads = Depends(get_sv_upload_section),
):
    return {"items": SiteVisitUploadCRUD(db_session).get_uploads(site_visit.id, upload_section.value)}


@sv_uploads_router.get(
    f"/{SiteVisitsUploads.site_conditions}/{{upload_id}}",
    response_model=FileDownloadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view))),
    ],
)
@sv_uploads_router.get(
    f"/{SiteVisitsUploads.field_discovery}/{{upload_id}}",
    response_model=FileDownloadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view))),
    ],
)
async def get_download_url(
    sv_upload: Attachment = Depends(get_authorized_site_visit_upload),
):
    return {"download_url": SiteVisitFileHandler().generate_download_signed_url(sv_upload.filepath, sv_upload.filename)}


@sv_uploads_router.delete(
    f"/{SiteVisitsUploads.site_conditions}/{{upload_id}}",
    response_model=FileRemovalSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.edit))),
    ],
)
@sv_uploads_router.delete(
    f"/{SiteVisitsUploads.field_discovery}/{{upload_id}}",
    response_model=FileRemovalSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.edit))),
    ],
)
async def remove_attachment(
    upload_id: int,
    db_session: Session = Depends(get_session),
    sv_upload: Attachment = Depends(get_authorized_site_visit_upload),
):
    # first, remove file from GCS
    error = SiteVisitFileHandler().delete_file(sv_upload.filepath)
    if error:
        raise HTTPException(error["code"], error["message"])
    # then remove record from DB
    SiteVisitUploadCRUD(db_session).delete_by_id(upload_id)
    return {"code": status.HTTP_200_OK, "message": "File has been successfully deleted"}


@sv_uploads_router.get(
    f"/{SiteVisitsUploads.site_conditions}/{{upload_id}}/file-preview-url",
    response_model=FilePreviewURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get file preview url.",
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view))),
    ],
)
@sv_uploads_router.get(
    f"/{SiteVisitsUploads.field_discovery}/{{upload_id}}/file-preview-url",
    response_model=FilePreviewURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get file preview url.",
    dependencies=[
        Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view))),
    ],
)
async def attachment_view_url(
    sv_upload: Attachment = Depends(get_authorized_site_visit_upload),
):
    return {"preview_url": SiteVisitFileHandler().generate_file_view_signed_url(sv_upload.filepath, sv_upload.filename)}
