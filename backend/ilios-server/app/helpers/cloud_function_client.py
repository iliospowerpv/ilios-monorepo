import logging
import os

import google.auth.transport.requests
import google.oauth2.id_token
import requests
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account
from requests import HTTPError

from app.models.file import File
from app.settings import settings

logger = logging.getLogger(__name__)


class BaseCloudFuncHTTPClient:
    def __init__(self, func_url):
        self.func_url = func_url
        credentials = service_account.Credentials.from_service_account_file(
            settings.service_account_key_file_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.authorized_session = AuthorizedSession(credentials)
        # Setup env variable for token authentication
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.service_account_key_file_path

    def post(self, payload=None, params=None, headers=None, use_token=False, use_api_key=False):
        headers = {"Content-Type": "application/json", **(headers if headers else {})}
        if use_token:
            # Some cloud functions require token authorization
            auth_req = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(auth_req, self.func_url)
            headers["Authorization"] = f"Bearer {id_token}"
            session = requests
        elif use_api_key:
            # ML-services are publicly accessible, and they required api_key as param
            session = requests
            # ensure param is a valid dict
            if not params:
                params = {}
            params.update({"api_key": settings.ml_api_key})
        else:
            session = self.authorized_session

        response = session.post(
            self.func_url,
            params=params,
            json=payload,
            headers=headers,
        )

        try:
            response.raise_for_status()
        except HTTPError:
            logger.exception("Got an error while trying to call Cloud Function")
        return response


class FileParseFuncHTTPClient(BaseCloudFuncHTTPClient):
    def __init__(self, func_url=None):
        self.func_url = func_url or settings.file_parse_function_url
        super().__init__(self.func_url)

    @staticmethod
    def prepare_trigger_payload(file: File, ai_record_id: int, agreement_type: str):  # noqa VNE002
        # create GSutil-like file URL
        file_url = f"gs://{settings.due_diligence_gcs_bucket}/{file.filepath}"
        return {
            "id": ai_record_id,
            "detect_poison_pills": True,
            "file_url": file_url,
            "agreement_type": agreement_type,
        }


class AIServerClient(BaseCloudFuncHTTPClient):
    def __init__(self, func_url):
        self.func_url = func_url
        super().__init__(self.func_url)
