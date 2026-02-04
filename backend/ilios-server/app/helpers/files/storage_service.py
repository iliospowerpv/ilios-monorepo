"""Storage Service Abstraction

Provides a unified interface for file storage operations.
Supports both legacy GCS buckets and Replit Object Storage.

Usage:
    # For new files, use Replit storage:
    storage = get_storage_service()
    
    # For legacy GCS files:
    storage = get_storage_service(storage_type="gcs", bucket_name="bucket")
"""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.cloud import storage
from google.oauth2 import service_account

from app.settings import settings
from app.static.files import FILE_PREVIEW_CONTENT_TYPE_MAPPING, FILE_UPLOAD_CONTENT_TYPE_MAPPING

logger = logging.getLogger(__name__)


class StorageService(ABC):
    """Abstract base class for storage operations."""
    
    @abstractmethod
    def upload_from_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Upload bytes to storage, returns the storage key."""
        pass
    
    @abstractmethod
    def download_as_bytes(self, key: str) -> bytes:
        """Download file as bytes."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a file from storage."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a file exists."""
        pass
    
    @abstractmethod
    def generate_upload_url(self, key: str, content_type: str, expiration_minutes: int = 15) -> str:
        """Generate a presigned URL for uploading."""
        pass
    
    @abstractmethod
    def generate_download_url(self, key: str, filename: str, expiration_minutes: int = 15) -> str:
        """Generate a presigned URL for downloading."""
        pass
    
    @abstractmethod
    def generate_preview_url(self, key: str, filename: str, expiration_minutes: int = 15) -> str:
        """Generate a presigned URL for previewing (inline display)."""
        pass


class GCSStorageService(StorageService):
    """Google Cloud Storage implementation using service account credentials."""
    
    def __init__(self, bucket_name: str):
        credentials = service_account.Credentials.from_service_account_file(
            settings.service_account_key_file_path
        )
        storage_client = storage.Client(credentials=credentials)
        self.bucket = storage_client.bucket(bucket_name)
        self.bucket_name = bucket_name
    
    def upload_from_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        blob = self.bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        return key
    
    def download_as_bytes(self, key: str) -> bytes:
        blob = self.bucket.blob(key)
        return blob.download_as_bytes()
    
    def delete(self, key: str) -> None:
        try:
            blob = self.bucket.blob(key)
            blob.reload()
            generation_match_precondition = blob.generation
            blob.delete(if_generation_match=generation_match_precondition)
        except Exception as exc:
            logger.warning(f"Error deleting file {key}: {exc}")
    
    def exists(self, key: str) -> bool:
        blob = self.bucket.blob(key)
        return blob.exists()
    
    def generate_upload_url(self, key: str, content_type: str, expiration_minutes: int = 15) -> str:
        return self.bucket.blob(key).generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="PUT",
            content_type=content_type,
        )
    
    def generate_download_url(self, key: str, filename: str, expiration_minutes: int = 15) -> str:
        blob = self.bucket.blob(key)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
            response_disposition=f"attachment;filename={filename}",
        )
    
    def generate_preview_url(self, key: str, filename: str, expiration_minutes: int = 15) -> str:
        file_extension = filename.split(".")[-1].lower()
        if file_extension not in FILE_PREVIEW_CONTENT_TYPE_MAPPING:
            available_extensions = ", ".join(FILE_PREVIEW_CONTENT_TYPE_MAPPING)
            raise ValueError(f"Only {available_extensions} files are available to preview.")
        
        blob = self.bucket.blob(key)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
            response_disposition=f"filename={filename}",
            response_type=FILE_PREVIEW_CONTENT_TYPE_MAPPING.get(file_extension),
        )


class ReplitStorageService(StorageService):
    """Replit Object Storage implementation.
    
    Uses the default bucket configured in the Replit environment.
    Files are stored with keys prefixed by storage_type for organization.
    """
    
    def __init__(self, storage_prefix: str = "ilios"):
        self._client = None
        self.storage_prefix = storage_prefix
    
    @property
    def client(self):
        if self._client is None:
            try:
                from replit.object_storage import Client
                self._client = Client()
            except ImportError:
                raise RuntimeError(
                    "replit-object-storage package not installed. "
                    "Install with: pip install replit-object-storage"
                )
        return self._client
    
    def _prefixed_key(self, key: str) -> str:
        return f"{self.storage_prefix}/{key}"
    
    def upload_from_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        full_key = self._prefixed_key(key)
        self.client.upload_from_bytes(full_key, data)
        return full_key
    
    def download_as_bytes(self, key: str) -> bytes:
        return self.client.download_as_bytes(key)
    
    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except Exception as exc:
            logger.warning(f"Error deleting file {key}: {exc}")
    
    def exists(self, key: str) -> bool:
        return self.client.exists(key)
    
    def generate_upload_url(self, key: str, content_type: str, expiration_minutes: int = 15) -> str:
        raise NotImplementedError(
            "Replit Object Storage uses direct upload via SDK, not presigned URLs for uploads. "
            "Use upload_from_bytes() instead or implement a custom upload endpoint."
        )
    
    def generate_download_url(self, key: str, filename: str, expiration_minutes: int = 15) -> str:
        raise NotImplementedError(
            "Replit Object Storage uses direct download via SDK. "
            "Implement a download endpoint that streams the file."
        )
    
    def generate_preview_url(self, key: str, filename: str, expiration_minutes: int = 15) -> str:
        raise NotImplementedError(
            "Replit Object Storage uses direct download via SDK. "
            "Implement a preview endpoint that streams the file."
        )


class HybridStorageService(StorageService):
    """Hybrid storage that uses GCS for presigned URLs but can fall back to Replit storage."""
    
    def __init__(self, bucket_name: str, use_replit_for_new: bool = False):
        self.gcs = GCSStorageService(bucket_name)
        self.use_replit_for_new = use_replit_for_new
        self._replit = None
    
    @property
    def replit(self) -> ReplitStorageService:
        if self._replit is None:
            self._replit = ReplitStorageService()
        return self._replit
    
    def upload_from_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        if self.use_replit_for_new:
            return self.replit.upload_from_bytes(key, data, content_type)
        return self.gcs.upload_from_bytes(key, data, content_type)
    
    def download_as_bytes(self, key: str) -> bytes:
        if key.startswith("ilios/"):
            return self.replit.download_as_bytes(key)
        return self.gcs.download_as_bytes(key)
    
    def delete(self, key: str) -> None:
        if key.startswith("ilios/"):
            self.replit.delete(key)
        else:
            self.gcs.delete(key)
    
    def exists(self, key: str) -> bool:
        if key.startswith("ilios/"):
            return self.replit.exists(key)
        return self.gcs.exists(key)
    
    def generate_upload_url(self, key: str, content_type: str, expiration_minutes: int = 15) -> str:
        return self.gcs.generate_upload_url(key, content_type, expiration_minutes)
    
    def generate_download_url(self, key: str, filename: str, expiration_minutes: int = 15) -> str:
        return self.gcs.generate_download_url(key, filename, expiration_minutes)
    
    def generate_preview_url(self, key: str, filename: str, expiration_minutes: int = 15) -> str:
        return self.gcs.generate_preview_url(key, filename, expiration_minutes)


_storage_services: dict = {}


def get_storage_service(
    storage_type: str = "gcs",
    bucket_name: Optional[str] = None,
) -> StorageService:
    """Factory function to get appropriate storage service.
    
    Args:
        storage_type: "gcs", "replit", or "hybrid"
        bucket_name: Required for GCS and hybrid storage types
    
    Returns:
        StorageService instance
    """
    cache_key = f"{storage_type}:{bucket_name}"
    
    if cache_key not in _storage_services:
        if storage_type == "gcs":
            if not bucket_name:
                raise ValueError("bucket_name is required for GCS storage")
            _storage_services[cache_key] = GCSStorageService(bucket_name)
        elif storage_type == "replit":
            _storage_services[cache_key] = ReplitStorageService()
        elif storage_type == "hybrid":
            if not bucket_name:
                raise ValueError("bucket_name is required for hybrid storage")
            _storage_services[cache_key] = HybridStorageService(bucket_name)
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
    
    return _storage_services[cache_key]


def generate_storage_key(
    company_id: int,
    site_id: int,
    document_id: int,
    filename: str,
) -> str:
    """Generate a unique storage key for a file.
    
    Format: companies/{company_id}/sites/{site_id}/documents/{document_id}/{timestamp}_{filename}
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return f"companies/{company_id}/sites/{site_id}/documents/{document_id}/{timestamp}_{filename}"
