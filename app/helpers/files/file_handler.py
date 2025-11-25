import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from google.api_core.exceptions import NotFound
from google.cloud import storage
from google.oauth2 import service_account

from app.settings import settings
from app.static.files import FILE_PREVIEW_CONTENT_TYPE_MAPPING, FILE_UPLOAD_CONTENT_TYPE_MAPPING

logger = logging.getLogger(__name__)


class FileHandler:
    """Class to handle actions related to Google Cloud Storage.

    Note that Google Cloud Storage Client requires a service account key file. You can not use this if you are
    using Application Default Credentials from Google ComputeEngine or from the Google Cloud SDK.

    Path to service account key file is stored under 'service_account_key_file_path' settings variable.
    """

    def __init__(self, bucket_name: str):
        credentials = service_account.Credentials.from_service_account_file(settings.service_account_key_file_path)
        storage_client = storage.Client(credentials=credentials)
        self.bucket = storage_client.bucket(bucket_name)

    @staticmethod
    def _generate_name(filename):
        """Generate filename with timestamp to ensure filename is unique in the storage"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        return f"{timestamp}_{filename}"

    def delete_file(self, filepath):
        """Docs: https://cloud.google.com/storage/docs/deleting-objects#client-libraries"""
        try:
            blob = self.bucket.blob(filepath)

            # Fetch blob metadata to use in generation_match_precondition.
            blob.reload()
            # Set a generation-match precondition to avoid potential race conditions and data corruptions.
            # The request to delete is aborted if the object's generation number does not match your precondition.
            generation_match_precondition = blob.generation

            blob.delete(if_generation_match=generation_match_precondition)
        except NotFound:
            # Handle 404 error do not block the main execution:
            # if file was removed already from storage, print the message and allow further processing
            logger.warning(f"Can not locate file by GCS path {filepath}")
        except Exception as exc:
            logger.error(f"Cannot remove file {filepath}, an error {str(exc)}")
            return json.loads(exc.response.content)["error"]

    def generate_download_signed_url(self, filepath, filename):
        """Generates a v4 signed Google Storage URL for downloading a file."""

        blob = self.bucket.blob(filepath)
        signed_download_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=settings.file_download_link_expiration_minutes),
            method="GET",
            # Save file with initial file name from upload
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
                status.HTTP_400_BAD_REQUEST, detail=f"Only {available_extensions} files are available to preview."
            )

        blob = self.bucket.blob(filepath)
        signed_preview_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=settings.file_download_link_expiration_minutes),
            method="GET",
            # Save file with initial file name from upload
            response_disposition=f"filename={filename}",
            # use pdf response type for preview
            response_type=FILE_PREVIEW_CONTENT_TYPE_MAPPING.get(file_extension),
        )
        return signed_preview_url


class TaskAttachmentHandler(FileHandler):
    def __init__(self):
        super().__init__(bucket_name=settings.task_attachments_gcs_bucket)

    @staticmethod
    def _generate_attachment_path(board_id, task_id):
        """To support proper structure of file storage, create or retrieve the folder where to place the file"""
        return f"boards/{board_id}/tasks/{task_id}"

    def generate_gcs_attachment_filepath(self, board_id, task_id, filename):
        return f"{self._generate_attachment_path(board_id, task_id)}/{self._generate_name(filename)}"


class DeviceDocumentFileHandler(FileHandler):
    def __init__(self):
        super().__init__(bucket_name=settings.device_documents_gcs_bucket)

    @staticmethod
    def _generate_device_document_path(site_id, device_id):
        """To support proper structure of file storage, create or retrieve the folder where to place the file"""
        return f"sites/{site_id}/devices/{device_id}/documents"

    def generate_device_document_gcs_filepath(self, site_id, device_id, filename):
        return f"{self._generate_device_document_path(site_id, device_id)}/{self._generate_name(filename)}"


class DueDiligenceFileHandler(FileHandler):
    def __init__(self):
        super().__init__(bucket_name=settings.due_diligence_gcs_bucket)

    @staticmethod
    def _generate_path(company_id, site_id, document_id):
        """To support proper structure of file storage, create or retrieve the folder where to place the file"""
        return f"companies/{company_id}/sites/{site_id}/documents/{document_id}"

    def generate_due_diligence_gcs_filepath(self, company_id, site_id, document_id, filename):
        return f"{self._generate_path(company_id, site_id, document_id)}/{self._generate_name(filename)}"


class SiteVisitFileHandler(FileHandler):
    def __init__(self):
        super().__init__(bucket_name=settings.sv_uploads_gcs_bucket)

    def generate_site_visit_upload_gcs_filepath(self, site_visit_id: int, filename: str, section_name: str):
        return f"{site_visit_id}/{section_name}/{self._generate_name(filename)}"
