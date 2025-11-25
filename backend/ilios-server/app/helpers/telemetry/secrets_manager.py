import logging
from functools import wraps

from fastapi import HTTPException
from google.cloud.secretmanager import SecretManagerServiceClient
from google.oauth2 import service_account

from app.settings import settings

logger = logging.getLogger(__name__)


class GCPSecretsManager:
    """Class to handle actions related to Google Cloud Secrets.

    Note that Google Cloud Storage Client requires a service account key file. You can not use this if you are
    using Application Default Credentials from Google ComputeEngine or from the Google Cloud SDK.

    Path to service account key file is stored under 'service_account_key_file_path' settings variable.
    """

    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(settings.service_account_key_file_path)
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
