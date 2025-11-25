import logging
import pickle

import requests
from fastapi import HTTPException, status

from app.redis_cache.cache import get_cache
from app.settings import settings
from app.static import PBI_CONTENT_TYPE_HEADER, PowerBIMessages

logger = logging.getLogger(__name__)


class PowerBIHandler:
    def __init__(self):
        self.cache = get_cache()
        self.access_token_expiration = settings.pbi_access_token_expiration_seconds
        self.embed_token_expiration = settings.pbi_embed_token_expiration_seconds
        self.tenant_id = settings.pbi_tenant_id
        self.client_id = settings.pbi_client_id
        self.client_secret = settings.pbi_client_secret
        self.power_bi_workspace_id = settings.pbi_workspace_id
        self.power_bi_api_url = "https://api.powerbi.com/v1.0/myorg"
        self.token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        self.scope = "https://analysis.windows.net/powerbi/api/.default"  # Required for Power BI API

    def get_from_cache(self, key_name):
        cached_data = self.cache.get(key_name)
        if cached_data:
            return pickle.loads(cached_data)

    def set_cache(self, key_name, value, expiration_seconds):
        self.cache.set(key_name, pickle.dumps(value), ex=expiration_seconds)

    @staticmethod
    def _make_api_call(url, method, data=None, params=None, headers=None, json=None):
        """Wrapper around requests lib to log request details and handle errors"""
        logger.debug(f"Making a PowerBI request: {method=}, {url=}, {data=}, {params=}, {headers=}")
        response = requests.request(url=url, method=method, params=params, data=data, headers=headers, json=json)
        logger.debug(f"Got PowerBI response for {method=} {url=}: {response.status_code=}")
        if not response.ok:
            logger.error(f"An error occured while making PowerBI request: {url=}, {response.status_code=}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=PowerBIMessages.service_unavailable)
        return response

    def _generate_access_token(self):
        """Get access token for the application.

        docs: https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow#get-a-token"""
        # try to get cached token value
        token_cache_key = "powerbi-token"
        cached_token = self.get_from_cache(token_cache_key)
        if cached_token:
            return cached_token
        # make an API call if no cached token found
        token_payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope,
        }
        response = self._make_api_call(url=self.token_url, method="POST", data=token_payload)
        access_token = response.json().get("access_token")
        self.set_cache(token_cache_key, access_token, self.access_token_expiration)
        return access_token

    def list_reports(self):
        """Returns a list of reports for specific group (aka workspace):

        docs: https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-reports-in-group"""
        access_token = self._generate_access_token()
        url = f"{self.power_bi_api_url}/groups/{self.power_bi_workspace_id}/reports"

        headers = {"Authorization": f"Bearer {access_token}"}
        response = self._make_api_call(url=url, method="GET", headers=headers)
        return response.json()["value"]

    def generate_embed_token(self, report_id: str):
        """Generate embedding token for the specified report id,
        cache value to limit PBI calls

        docs: https://learn.microsoft.com/en-us/rest/api/power-bi/embed-token/reports-generate-token-in-group
        """
        embed_token_cache_key = f"powerbi-embed-token-{report_id}"
        cached_token = self.get_from_cache(embed_token_cache_key)
        if cached_token:
            return cached_token
        access_token = self._generate_access_token()
        url = f"{self.power_bi_api_url}/groups/{self.power_bi_workspace_id}/reports/{report_id}/GenerateToken"
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = {"accessLevel": "View"}
        response = self._make_api_call(url=url, method="POST", headers=headers, data=payload)
        embed_token = response.json()["token"]
        self.set_cache(embed_token_cache_key, embed_token, self.embed_token_expiration)
        return embed_token

    def get_report_pages(self, report_id: str):
        """Returns specific report pages

        docs: https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-pages-in-group"""
        access_token = self._generate_access_token()
        url = f"{self.power_bi_api_url}/groups/{self.power_bi_workspace_id}/reports/{report_id}/pages"

        headers = {"Authorization": f"Bearer {access_token}"}
        response = self._make_api_call(url=url, method="GET", headers=headers)
        return response.json()

    def export_report_to_file(self, report_id: str, payload: dict):
        """Export specified report to the file with various input settings.

        docs: https://learn.microsoft.com/en-us/rest/api/power-bi/reports/export-to-file-in-group
        """
        access_token = self._generate_access_token()
        url = f"{self.power_bi_api_url}/groups/{self.power_bi_workspace_id}/reports/{report_id}/ExportTo"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; odata.metadata=minimal"}
        response = self._make_api_call(url=url, method="POST", headers=headers, json=payload)
        return response.json()

    def get_export_status(self, report_id: str, export_id: str):
        """Retrieve specified export status.

        docs: https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-export-to-file-status-in-group
        """
        access_token = self._generate_access_token()
        url = f"{self.power_bi_api_url}/groups/{self.power_bi_workspace_id}/reports/{report_id}/exports/{export_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self._make_api_call(url=url, method="GET", headers=headers)
        return response.json()

    def get_export_file(self, report_id: str, export_id: str):
        """Retrieve content of exported file.

        docs: https://learn.microsoft.com/en-us/rest/api/power-bi/reports/get-file-of-export-to-file-in-group
        """
        access_token = self._generate_access_token()
        url = f"{self.power_bi_api_url}/groups/{self.power_bi_workspace_id}/reports/{report_id}/exports/{export_id}/file"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = self._make_api_call(url=url, method="GET", headers=headers)
        content_type = response.headers.get(PBI_CONTENT_TYPE_HEADER, "application/octet-stream")
        return response.content, content_type
