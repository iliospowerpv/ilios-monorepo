"""Storage Service Abstraction

Provides a unified interface for file storage operations.
Supports Replit Object Storage (default) and legacy GCS (optional fallback).

IMPORTANT: GCS imports are LAZY - only loaded when storage_provider="gcs".
This allows the app to boot and run without any Google Cloud dependencies.

Usage:
    storage = get_storage_service()  # Returns Replit storage by default
    storage.upload_bytes("key", data, "application/pdf")
    data = storage.download_bytes("key")
"""

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from app.settings import settings

if TYPE_CHECKING:
    from google.cloud.storage import Bucket

logger = logging.getLogger(__name__)


class StorageService(ABC):
    """Abstract base class for storage operations."""

    @abstractmethod
    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Upload bytes to storage, returns the storage key."""
        pass

    @abstractmethod
    def download_bytes(self, key: str) -> bytes:
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
    def get_content_type(self, key: str) -> Optional[str]:
        """Get the content type of a file."""
        pass


class ReplitStorageService(StorageService):
    """Replit Object Storage implementation.

    Uses the Replit Object Storage SDK for all operations.
    No external credentials required - auth is handled by Replit environment.
    """

    def __init__(self, storage_prefix: str = "ilios"):
        self._client = None
        self.storage_prefix = storage_prefix
        logger.info(f"ReplitStorageService initialized with prefix: {storage_prefix}")

    @property
    def client(self):
        if self._client is None:
            try:
                from replit.object_storage import Client
                self._client = Client()
                logger.info("Replit Object Storage client initialized successfully")
            except ImportError as e:
                raise RuntimeError(
                    "replit-object-storage package not installed. "
                    "Install with: pip install replit-object-storage"
                ) from e
            except Exception as e:
                logger.error(f"Failed to initialize Replit Object Storage client: {e}")
                raise
        return self._client

    def _prefixed_key(self, key: str) -> str:
        """Add storage prefix to key if not already present."""
        if key.startswith(f"{self.storage_prefix}/"):
            return key
        return f"{self.storage_prefix}/{key}"

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Upload bytes to Replit Object Storage."""
        full_key = self._prefixed_key(key)
        try:
            self.client.upload_from_bytes(full_key, data)
            logger.info(f"Uploaded {len(data)} bytes to Replit storage: {full_key}")
            return full_key
        except Exception as e:
            logger.error(f"Failed to upload to Replit storage {full_key}: {e}")
            raise

    def download_bytes(self, key: str) -> bytes:
        """Download file bytes from Replit Object Storage."""
        try:
            data = self.client.download_as_bytes(key)
            logger.info(f"Downloaded {len(data)} bytes from Replit storage: {key}")
            return data
        except Exception as e:
            logger.error(f"Failed to download from Replit storage {key}: {e}")
            raise

    def delete(self, key: str) -> None:
        """Delete a file from Replit Object Storage."""
        try:
            self.client.delete(key)
            logger.info(f"Deleted from Replit storage: {key}")
        except Exception as e:
            logger.warning(f"Error deleting file {key} from Replit storage: {e}")

    def exists(self, key: str) -> bool:
        """Check if a file exists in Replit Object Storage."""
        try:
            return self.client.exists(key)
        except Exception as e:
            logger.warning(f"Error checking existence of {key}: {e}")
            return False

    def get_content_type(self, key: str) -> Optional[str]:
        """Infer content type from key extension."""
        ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
        content_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
        }
        return content_types.get(ext, "application/octet-stream")


class GCSStorageService(StorageService):
    """Google Cloud Storage implementation using service account credentials.

    IMPORTANT: This class lazily imports google.cloud libraries.
    GCS is only used when explicitly configured via STORAGE_PROVIDER="gcs".
    """

    def __init__(self, bucket_name: str):
        self._bucket: Optional["Bucket"] = None
        self._bucket_name = bucket_name
        logger.info(f"GCSStorageService initialized for bucket: {bucket_name}")

    @property
    def bucket(self) -> "Bucket":
        """Lazily initialize the GCS bucket connection."""
        if self._bucket is None:
            # LAZY IMPORT - only when actually needed
            try:
                from google.cloud import storage
                from google.oauth2 import service_account

                if not settings.service_account_key_file_path:
                    raise ValueError(
                        "GCS storage requires service_account_key_file_path setting"
                    )

                credentials = service_account.Credentials.from_service_account_file(
                    settings.service_account_key_file_path
                )
                storage_client = storage.Client(credentials=credentials)
                self._bucket = storage_client.bucket(self._bucket_name)
                logger.info(f"GCS bucket connection established: {self._bucket_name}")
            except ImportError as e:
                raise RuntimeError(
                    "google-cloud-storage package not installed. "
                    "Install with: pip install google-cloud-storage"
                ) from e
        return self._bucket

    def upload_bytes(self, key: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Upload bytes to GCS."""
        blob = self.bucket.blob(key)
        blob.upload_from_string(data, content_type=content_type)
        logger.info(f"Uploaded {len(data)} bytes to GCS: {key}")
        return key

    def download_bytes(self, key: str) -> bytes:
        """Download file bytes from GCS."""
        blob = self.bucket.blob(key)
        data = blob.download_as_bytes()
        logger.info(f"Downloaded {len(data)} bytes from GCS: {key}")
        return data

    def delete(self, key: str) -> None:
        """Delete a file from GCS."""
        try:
            blob = self.bucket.blob(key)
            blob.reload()
            generation_match_precondition = blob.generation
            blob.delete(if_generation_match=generation_match_precondition)
            logger.info(f"Deleted from GCS: {key}")
        except Exception as e:
            logger.warning(f"Error deleting file {key} from GCS: {e}")

    def exists(self, key: str) -> bool:
        """Check if a file exists in GCS."""
        blob = self.bucket.blob(key)
        return blob.exists()

    def get_content_type(self, key: str) -> Optional[str]:
        """Get content type from GCS blob metadata."""
        try:
            blob = self.bucket.blob(key)
            blob.reload()
            return blob.content_type
        except Exception:
            return None


# Module-level cache for storage services
_storage_services: dict = {}


def get_storage_service(
    storage_type: Optional[str] = None,
    bucket_name: Optional[str] = None,
) -> StorageService:
    """Factory function to get appropriate storage service.

    Args:
        storage_type: "replit" or "gcs". Defaults to settings.storage_provider.
        bucket_name: Required for GCS storage type.

    Returns:
        StorageService instance
    """
    # Default to settings if not specified
    if storage_type is None:
        storage_type = settings.storage_provider.lower()

    cache_key = f"{storage_type}:{bucket_name or 'default'}"

    if cache_key not in _storage_services:
        if storage_type == "replit":
            _storage_services[cache_key] = ReplitStorageService(
                storage_prefix=settings.replit_storage_prefix
            )
        elif storage_type == "gcs":
            if not bucket_name:
                raise ValueError("bucket_name is required for GCS storage")
            _storage_services[cache_key] = GCSStorageService(bucket_name)
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

    Format: companies/{company_id}/sites/{site_id}/documents/{document_id}/{iso_ts}_{sanitized_filename}
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    # Sanitize filename: remove/replace problematic characters
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
    return f"companies/{company_id}/sites/{site_id}/documents/{document_id}/{timestamp}_{sanitized}"


def get_legacy_gcs_service(bucket_name: str) -> Optional[GCSStorageService]:
    """Get a GCS service for reading legacy files.

    Only works if STORAGE_PROVIDER="gcs" is configured.
    Returns None if GCS is not configured (app is Replit-native).
    """
    if settings.storage_provider.lower() != "gcs":
        logger.warning(
            f"Legacy GCS read requested for bucket {bucket_name}, "
            "but STORAGE_PROVIDER is not 'gcs'. Returning None."
        )
        return None

    if not settings.service_account_key_file_path:
        logger.warning("GCS legacy read requested but no service account configured")
        return None

    return get_storage_service(storage_type="gcs", bucket_name=bucket_name)
