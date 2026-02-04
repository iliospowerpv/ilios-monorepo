"""File Handler Module

Provides file handling abstractions for different storage contexts.
IMPORTANT: All GCS imports are LAZY to allow app boot without Google Cloud credentials.

Usage:
    For new uploads (Replit storage):
        from app.helpers.files.storage_service import get_storage_service, generate_storage_key
        storage = get_storage_service()
        key = generate_storage_key(company_id, site_id, document_id, filename)
        storage.upload_bytes(key, data, content_type)

    For legacy GCS operations (when storage_provider="gcs"):
        handler = DueDiligenceFileHandler()  # Only works with GCS config
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, status

from app.settings import settings
from app.static.files import FILE_PREVIEW_CONTENT_TYPE_MAPPING, FILE_UPLOAD_CONTENT_TYPE_MAPPING

if TYPE_CHECKING:
    from google.cloud.storage import Bucket

logger = logging.getLogger(__name__)


def _get_gcs_bucket(bucket_name: str) -> "Bucket":
    """Lazily create a GCS bucket connection.

    IMPORTANT: Google Cloud imports happen here, not at module level.
    This allows the app to boot and run without GCS credentials when using Replit storage.
    """
    if settings.storage_provider.lower() == "replit":
        raise RuntimeError(
            "GCS bucket access requested but STORAGE_PROVIDER='replit'. "
            "Use storage_service.get_storage_service() for Replit storage operations."
        )

    if not settings.service_account_key_file_path:
        raise RuntimeError(
            "GCS bucket access requires service_account_key_file_path setting. "
            "Configure GCS credentials or use STORAGE_PROVIDER='replit'."
        )

    try:
        from google.cloud import storage
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            settings.service_account_key_file_path
        )
        storage_client = storage.Client(credentials=credentials)
        return storage_client.bucket(bucket_name)
    except ImportError as e:
        raise RuntimeError(
            "google-cloud-storage package not installed. "
            "Install with: pip install google-cloud-storage"
        ) from e
    except FileNotFoundError:
        raise RuntimeError(
            f"GCS service account key file not found: {settings.service_account_key_file_path}. "
            "Configure GCS credentials or use STORAGE_PROVIDER='replit'."
        )


class FileHandler:
    """Legacy GCS-based file handler.

    IMPORTANT: This class only works when STORAGE_PROVIDER="gcs" is configured.
    For Replit-native storage, use storage_service.get_storage_service() instead.

    The bucket is lazily initialized to avoid importing google.cloud at module level.
    """

    def __init__(self, bucket_name: str):
        self._bucket_name = bucket_name
        self._bucket: "Bucket" = None

    @property
    def bucket(self) -> "Bucket":
        """Lazily initialize the GCS bucket."""
        if self._bucket is None:
            self._bucket = _get_gcs_bucket(self._bucket_name)
        return self._bucket

    @staticmethod
    def _generate_name(filename):
        """Generate filename with timestamp to ensure filename is unique in the storage"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        return f"{timestamp}_{filename}"

    def delete_file(self, filepath):
        """Docs: https://cloud.google.com/storage/docs/deleting-objects#client-libraries"""
        try:
            from google.api_core.exceptions import NotFound

            blob = self.bucket.blob(filepath)
            blob.reload()
            generation_match_precondition = blob.generation
            blob.delete(if_generation_match=generation_match_precondition)
        except ImportError:
            logger.error("google-cloud-storage not installed, cannot delete file")
        except Exception as exc:
            if exc.__class__.__name__ == "NotFound":
                logger.warning(f"Can not locate file by GCS path {filepath}")
            else:
                logger.error(f"Cannot remove file {filepath}, an error {str(exc)}")

    def generate_download_signed_url(self, filepath, filename):
        """Generates a v4 signed Google Storage URL for downloading a file."""
        blob = self.bucket.blob(filepath)
        signed_download_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=settings.file_download_link_expiration_minutes),
            method="GET",
            response_disposition=f"attachment;filename={filename}",
        )
        return signed_download_url

    def generate_signed_url_for_upload(self, filepath, file_extension):
        content_type = FILE_UPLOAD_CONTENT_TYPE_MAPPING.get(file_extension)
        return self.bucket.blob(filepath).generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=settings.file_download_link_expiration_minutes),
            method="PUT",
            content_type=content_type,
        )

    def generate_file_view_signed_url(self, filepath, filename):
        """Generates a v4 signed Google Storage URL for preview .pdf, .jpeg, .png file."""
        file_extension = filename.split(".")[-1]
        if file_extension not in FILE_PREVIEW_CONTENT_TYPE_MAPPING.keys():
            available_extensions = ", ".join(FILE_PREVIEW_CONTENT_TYPE_MAPPING)
            logger.warning(f"File <{file_extension}> is not in a list of file types available for preview")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Only {available_extensions} files are available to preview.",
            )

        blob = self.bucket.blob(filepath)
        signed_preview_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=settings.file_download_link_expiration_minutes),
            method="GET",
            response_disposition=f"filename={filename}",
            response_type=FILE_PREVIEW_CONTENT_TYPE_MAPPING.get(file_extension),
        )
        return signed_preview_url


class TaskAttachmentHandler(FileHandler):
    def __init__(self):
        if not settings.task_attachments_gcs_bucket:
            raise RuntimeError("task_attachments_gcs_bucket not configured")
        super().__init__(bucket_name=settings.task_attachments_gcs_bucket)

    @staticmethod
    def _generate_attachment_path(board_id, task_id):
        """To support proper structure of file storage, create or retrieve the folder where to place the file"""
        return f"boards/{board_id}/tasks/{task_id}"

    def generate_gcs_attachment_filepath(self, board_id, task_id, filename):
        return f"{self._generate_attachment_path(board_id, task_id)}/{self._generate_name(filename)}"


class DeviceDocumentFileHandler(FileHandler):
    def __init__(self):
        if not settings.device_documents_gcs_bucket:
            raise RuntimeError("device_documents_gcs_bucket not configured")
        super().__init__(bucket_name=settings.device_documents_gcs_bucket)

    @staticmethod
    def _generate_device_document_path(site_id, device_id):
        """To support proper structure of file storage, create or retrieve the folder where to place the file"""
        return f"sites/{site_id}/devices/{device_id}/documents"

    def generate_device_document_gcs_filepath(self, site_id, device_id, filename):
        return f"{self._generate_device_document_path(site_id, device_id)}/{self._generate_name(filename)}"


class DueDiligenceFileHandler(FileHandler):
    """Legacy GCS file handler for Due Diligence documents.

    IMPORTANT: Only use this when STORAGE_PROVIDER="gcs".
    For Replit storage, use the new /upload, /download, /preview endpoints in files.py.
    """

    def __init__(self):
        if not settings.due_diligence_gcs_bucket:
            raise RuntimeError(
                "due_diligence_gcs_bucket not configured. "
                "Use Replit storage endpoints or configure GCS bucket."
            )
        super().__init__(bucket_name=settings.due_diligence_gcs_bucket)

    @staticmethod
    def _generate_path(company_id, site_id, document_id):
        """To support proper structure of file storage, create or retrieve the folder where to place the file"""
        return f"companies/{company_id}/sites/{site_id}/documents/{document_id}"

    def generate_due_diligence_gcs_filepath(self, company_id, site_id, document_id, filename):
        return f"{self._generate_path(company_id, site_id, document_id)}/{self._generate_name(filename)}"


class SiteVisitFileHandler(FileHandler):
    def __init__(self):
        if not settings.sv_uploads_gcs_bucket:
            raise RuntimeError("sv_uploads_gcs_bucket not configured")
        super().__init__(bucket_name=settings.sv_uploads_gcs_bucket)

    def generate_site_visit_upload_gcs_filepath(self, site_visit_id: int, filename: str, section_name: str):
        return f"{site_visit_id}/{section_name}/{self._generate_name(filename)}"
