"""GCP Secret Manager wrapper used by telemetry V2 credential storage.

Authentication priority (first match wins):

1. ``GOOGLE_APPLICATION_CREDENTIALS_JSON`` env var
   The full service-account JSON key, stored inline as a Replit secret.
   Preferred for Replit deployments — no file is ever written to the
   container image and nothing is committed to the repo. The JSON is
   parsed in-memory and passed to
   ``service_account.Credentials.from_service_account_info``.
2. ``service_account_key_file_path`` setting
   Legacy file-mounted key. Still supported so older deployments and the
   chatbot/file-parse cloud-function helpers continue to work.
3. Application Default Credentials (ADC)
   Falls back to the Google client library's default discovery
   (``gcloud auth application-default``, GCE metadata, Workload
   Identity, etc.). Only useful outside Replit; on Replit this almost
   always means "no credentials" and the SDK call will raise.

Secret values are never logged. Errors during init log only the
exception type, not the body.
"""
import json
import logging
import os
from functools import wraps

from fastapi import HTTPException
from google.cloud.secretmanager import SecretManagerServiceClient
from google.oauth2 import service_account

from app.settings import settings

logger = logging.getLogger(__name__)


def _build_credentials():
    """Resolve service-account credentials per the priority list above.

    Returns ``None`` to signal "use ADC" (the SDK will pick up
    ``GOOGLE_APPLICATION_CREDENTIALS`` or platform metadata on its own).
    Raises ``ValueError`` only when an explicit source is present but
    malformed — a missing source falls through to the next option.
    """
    json_blob = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if json_blob:
        try:
            info = json.loads(json_blob)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS_JSON is set but is not valid JSON"
            ) from exc
        # `from_service_account_info` validates required keys
        # (client_email, private_key, token_uri, …) and raises ValueError
        # with a non-secret message if any are missing.
        return service_account.Credentials.from_service_account_info(info)

    key_path = getattr(settings, "service_account_key_file_path", None)
    if key_path and os.path.isfile(key_path):
        return service_account.Credentials.from_service_account_file(key_path)

    return None  # ADC


class GCPSecretsManager:
    """Class to handle actions related to Google Cloud Secrets.

    See module docstring for the auth-source priority order.
    """

    def __init__(self):
        credentials = _build_credentials()
        if credentials is None:
            # ADC path — let the SDK try platform-default discovery.
            self.secrets_client = SecretManagerServiceClient()
        else:
            self.secrets_client = SecretManagerServiceClient(credentials=credentials)
        self.project_id = settings.gcp_project_id

    @staticmethod
    def handle_response_error(error_message):
        def function_manager(secret_manager_method):
            @wraps(secret_manager_method)
            def wrapper(*args, **kwargs):
                try:
                    return secret_manager_method(*args, **kwargs)
                except Exception as error:
                    logger.error(f"{error_message} due to error: {error}")
                    raise HTTPException(error.code, error.message)

            return wrapper

        return function_manager

    @handle_response_error("Can not create GCP secret")
    def create_secret(self, secret_id):
        parent = f"projects/{self.project_id}"
        response = self.secrets_client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        logger.info(f"Created secret: {response.name}")

    @handle_response_error("Can not add GCP secret version")
    def add_secret_version(self, secret_id: str, payload: str):
        parent = self.secrets_client.secret_path(self.project_id, secret_id)
        # Convert the payload dictionary into bytes
        payload = payload.encode("UTF-8")
        response = self.secrets_client.add_secret_version(parent=parent, payload={"data": payload})
        logger.info(f"Added secret version: {response.name}")

    @handle_response_error("Can not delete GCP secret")
    def delete_secret(self, secret_id: str):
        name = self.secrets_client.secret_path(self.project_id, secret_id)
        self.secrets_client.delete_secret(request={"name": name})
        logger.info(f"Deleted secret: {name}")

    def get_secret_version_id(self, secret_id: str, version_id: str = "latest"):
        parent = self.secrets_client.secret_path(self.project_id, secret_id)
        return f"{parent}/versions/{version_id}"

    def access_secret_value(self, secret_id: str, version_id: str = "latest") -> str:
        """Fetch the decoded payload of a secret version.

        Used by the in-process telemetry v2 credential store to read
        credentials back at request time. The legacy DAS flow never
        needed this because it forwarded the resource path to GCP cloud
        functions which fetched the payload via their own service
        accounts.
        """
        name = f"{self.secrets_client.secret_path(self.project_id, secret_id)}/versions/{version_id}"
        response = self.secrets_client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
