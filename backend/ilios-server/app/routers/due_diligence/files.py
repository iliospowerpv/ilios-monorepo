import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.crud.file import FileCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_document, get_authorized_file
from app.helpers.permission_guards import require_module_permission
from app.helpers.chatbot.files_sync import ChatBotFilesSyncer
from app.helpers.configs.agreement_names_helper import AgreementNamesMappingHandler
from app.helpers.files.storage_service import get_storage_service, generate_storage_key
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
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, FileMessages
from app.static.files import FILE_PREVIEW_CONTENT_TYPE_MAPPING, FILE_UPLOAD_CONTENT_TYPE_MAPPING

logger = logging.getLogger(__name__)
files_router = APIRouter()


ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "xlsx", "xls", "png", "jpg", "jpeg"}


@files_router.get(
    "/",
    response_model=FilesList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_files_list(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
    return {"items": FileCRUD(db_session).get_document_files(document.id)}


@files_router.delete(
    "/{file_id}",
    response_model=FileRemovalSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Soft delete file (setting `deleted` flag to True)",
)
async def remove_file(
    background_tasks: BackgroundTasks,
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
    FileCRUD(db_session).update_by_id(file.id, {"deleted": True})
    # send AI trigger to untrack the file from the ChatBot storage
    ai_params = {"file_id": file.id}
    background_tasks.add_task(ChatBotFilesSyncer().delete_file, ai_params)
    return {"code": status.HTTP_200_OK, "message": "File has been successfully deleted"}


@files_router.get(
    "/{file_id}",
    response_model=FileDownloadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="[LEGACY/GCS ONLY] Get download signed URL. Use /{file_id}/download for Replit storage.",
)
async def get_download_url(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    """Legacy endpoint for GCS download URLs.

    DEPRECATED: Use GET /{file_id}/download for Replit Object Storage.
    This endpoint only works when STORAGE_PROVIDER="gcs".
    """
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    # Check if GCS is available
    if settings.storage_provider.lower() != "gcs":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Signed URLs require GCS storage. Use /{file_id}/download endpoint instead.",
        )

    try:
        from app.helpers.files.file_handler import DueDiligenceFileHandler

        return {"download_url": DueDiligenceFileHandler().generate_download_signed_url(file.filepath, file.filename)}
    except RuntimeError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@files_router.post(
    "/upload-url/",
    response_model=FileUploadURLSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="[LEGACY/GCS ONLY] Get presigned upload URL. Use /upload for Replit storage.",
)
async def get_upload_url(
    site_id: int,
    document_id: int,
    file_data: FileNameSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    """Legacy endpoint for GCS presigned uploads.

    DEPRECATED: Use POST /upload for Replit Object Storage.
    This endpoint only works when STORAGE_PROVIDER="gcs".
    """
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )

    # Check if GCS is available
    if settings.storage_provider.lower() != "gcs":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Presigned URLs require GCS storage. Use POST /upload for Replit storage.",
        )

    # Lazy import to avoid requiring GCS at boot
    try:
        from app.helpers.files.file_handler import DueDiligenceFileHandler

        file_extension = file_data.filename.split(".")[-1]
        file_handler = DueDiligenceFileHandler()
        filepath = file_handler.generate_due_diligence_gcs_filepath(
            document.site.company_id, site_id, document_id, file_data.filename
        )
        return {"filepath": filepath, "upload_url": file_handler.generate_signed_url_for_upload(filepath, file_extension)}
    except RuntimeError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@files_router.post(
    "/track-uploaded-file/",
    response_model=FileUploadSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Create a file record with uploaded file details",
)
async def create_uploaded_file(
    document_id: int,
    file_data: CreateFileSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
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
    description="[LEGACY/GCS ONLY] Get file preview signed URL. Use /{file_id}/preview for Replit storage.",
)
async def file_view_url(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    """Legacy endpoint for GCS preview URLs.

    DEPRECATED: Use GET /{file_id}/preview for Replit Object Storage.
    This endpoint only works when STORAGE_PROVIDER="gcs".
    """
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    # Check if GCS is available
    if settings.storage_provider.lower() != "gcs":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Signed URLs require GCS storage. Use /{file_id}/preview endpoint instead.",
        )

    try:
        from app.helpers.files.file_handler import DueDiligenceFileHandler

        return {"preview_url": DueDiligenceFileHandler().generate_file_view_signed_url(file.filepath, file.filename)}
    except RuntimeError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@files_router.put(
    "/{file_id}/file-is-actual/",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=FileUpdateIsActualSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def update_is_actual_file_status(
    is_actual_payload: FileIsActual,
    background_tasks: BackgroundTasks,
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
    FileCRUD(db_session).update_by_id(file.id, is_actual_payload.model_dump())
    # send AI trigger
    ai_params = {"actual": str(is_actual_payload.is_actual).lower(), "file_id": file.id}
    background_tasks.add_task(ChatBotFilesSyncer().mark_file_actual, ai_params)
    return {"code": status.HTTP_200_OK, "message": FileMessages.file_actual_status_updated}


@files_router.post(
    "/upload",
    response_model=FileUploadSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Upload a file directly to Replit Object Storage (backend-proxied upload)",
)
async def upload_file(
    site_id: int,
    document_id: int,
    file: UploadFile,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    """Upload file directly through backend to Replit Object Storage.

    This endpoint:
    1. Validates file extension and size
    2. Uploads file bytes to Replit Object Storage
    3. Creates a File database record with storage_key
    4. Handles versioning (increments version_number for same document)
    5. Triggers ChatBot sync in background
    """
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )

    # Validate file extension
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Filename is required")

    file_extension = file.filename.rsplit(".", 1)[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_extension}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > settings.allowed_filesize:
        max_mb = settings.allowed_filesize / (1024 * 1024)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed ({max_mb:.0f} MB)",
        )

    # Generate storage key
    storage_key = generate_storage_key(
        company_id=document.site.company_id,
        site_id=site_id,
        document_id=document_id,
        filename=file.filename,
    )

    # Upload to Replit Object Storage
    storage_service = get_storage_service()
    content_type = FILE_UPLOAD_CONTENT_TYPE_MAPPING.get(file_extension, "application/octet-stream")

    try:
        full_key = storage_service.upload_bytes(storage_key, content, content_type)
        logger.info(f"File uploaded to Replit storage: {full_key}")
    except Exception as e:
        logger.error(f"Failed to upload file to storage: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload file")

    # Determine version number (get_document_files already filters deleted=False)
    file_crud = FileCRUD(db_session)
    existing_files = file_crud.get_document_files(document_id)
    version_number = len(existing_files) + 1

    # Create file record
    file_payload = {
        "filename": file.filename,
        "filepath": storage_key,  # Legacy field - use storage_key for new files
        "storage_key": full_key,
        "document_id": document_id,
        "user_id": current_user.id,
        "version_number": version_number,
        "is_actual": False,  # New uploads are not actual by default
    }
    new_file = file_crud.create_item(file_payload)

    # Trigger ChatBot sync
    agreement_name = AgreementNamesMappingHandler(db_session).get_pipeline_agreement_name(document.name)
    if not agreement_name:
        agreement_name = "Other"

    section_name = document.section.name.value
    subsection_name = None
    if document.section.parent_section:
        section_name = document.section.parent_section.name.value
        subsection_name = document.section.name.value

    ai_payload = {
        "file_link": f"replit://{full_key}",  # Use replit:// scheme for Replit storage
        "file_id": new_file.id,
        "site_name": document.site.name,
        "site_id": document.site_id,
        "company_name": document.site.company.name,
        "company_id": document.site.company_id,
        "agreement_name": agreement_name,
        "document_name": document.name.value,
        "file_name": file.filename,
        "section_name": section_name,
        "subsection_name": subsection_name,
    }
    background_tasks.add_task(ChatBotFilesSyncer().upload_file, ai_payload)

    return {"code": status.HTTP_200_OK, "message": f"File successfully uploaded (version {version_number})"}


@files_router.get(
    "/{file_id}/download",
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Download file bytes from storage",
)
async def download_file(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    """Download file bytes from Replit Object Storage.

    Returns file content with proper content-type and disposition headers.
    Falls back to legacy GCS if storage_key is not set (only when storage_provider=gcs).
    """
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    # Determine which storage key to use
    storage_key = file.storage_key or file.filepath

    if not storage_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File storage key not found")

    # For files without storage_key (legacy), check if GCS fallback is available
    if not file.storage_key and settings.storage_provider.lower() != "gcs":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Legacy file requires GCS configuration. Set STORAGE_PROVIDER=gcs to access legacy files.",
        )

    try:
        storage_service = get_storage_service()
        content = storage_service.download_bytes(storage_key)
    except Exception as e:
        logger.error(f"Failed to download file {storage_key}: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to download file")

    # Determine content type
    file_extension = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    content_type = FILE_UPLOAD_CONTENT_TYPE_MAPPING.get(file_extension, "application/octet-stream")

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{file.filename}"',
            "Cache-Control": "no-cache",
        },
    )


@files_router.get(
    "/{file_id}/preview",
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Preview file (PDF, images) inline in browser",
)
async def preview_file(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    file: FileModel = Depends(get_authorized_file),
    db_session: Session = Depends(get_session),
):
    """Preview file inline in browser.

    Returns file content with inline disposition for PDF and image previews.
    Only supports PDF, PNG, JPG, JPEG files.
    """
    require_module_permission(
        user_id=current_user.id,
        company_id=file.document.site.company_id,
        project_id=file.document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    # Validate previewable file type
    file_extension = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if file_extension not in FILE_PREVIEW_CONTENT_TYPE_MAPPING:
        available = ", ".join(FILE_PREVIEW_CONTENT_TYPE_MAPPING.keys())
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_extension}' cannot be previewed. Supported: {available}",
        )

    # Determine which storage key to use
    storage_key = file.storage_key or file.filepath

    if not storage_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="File storage key not found")

    # For files without storage_key (legacy), check if GCS fallback is available
    if not file.storage_key and settings.storage_provider.lower() != "gcs":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Legacy file requires GCS configuration. Set STORAGE_PROVIDER=gcs to access legacy files.",
        )

    try:
        storage_service = get_storage_service()
        content = storage_service.download_bytes(storage_key)
    except Exception as e:
        logger.error(f"Failed to preview file {storage_key}: {e}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to preview file")

    content_type = FILE_PREVIEW_CONTENT_TYPE_MAPPING.get(file_extension, "application/octet-stream")

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{file.filename}"',
            "Cache-Control": "no-cache",
        },
    )
