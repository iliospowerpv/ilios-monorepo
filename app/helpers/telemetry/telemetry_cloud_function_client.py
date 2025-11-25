import logging

from fastapi import HTTPException, status

from app.helpers.cloud_function_client import BaseCloudFuncHTTPClient
from app.settings import settings
from app.static import TelemetryMessages

logger = logging.getLogger(__name__)


class TelemetryFuncHTTPClient(BaseCloudFuncHTTPClient):
    def __init__(self, func_url=None):
        self.func_url = func_url
        self.token_func_url = settings.telemetry_token_function_url
        self.sites_func_url = settings.telemetry_sites_function_url
        self.devices_func_url = settings.telemetry_devices_function_url
        self.device_static_info_func_url = settings.telemetry_device_static_info_func_url

        super().__init__(self.func_url)

    @staticmethod
    def handle_response_error(response):
        if response.status_code != status.HTTP_200_OK:
            response_message = None
            try:
                response_message = response.json()["message"]
            except Exception:
                pass
            logger.error(f"Telemetry call failed with status {response.status_code}, message: {response_message}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.das_provider_unavailable)

    def validate_token(self, provider, token):
        self.func_url = self.token_func_url
        payload = {
            "data_provider": provider,
            "token": token,
        }
        telemetry_response = self.post(payload=payload, use_token=True)
        if telemetry_response.status_code != status.HTTP_200_OK:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.token_validation_failed)

    def get_telemetry_sites(self, provider, token_secret_id):
        self.func_url = self.sites_func_url
        payload = {
            "data_provider": provider,
            "token_secret_id": token_secret_id,
        }
        telemetry_response = self.post(payload=payload, use_token=True)
        self.handle_response_error(telemetry_response)
        return telemetry_response.json()

    def get_telemetry_devices(self, provider, token_secret_id, telemetry_site_id):
        self.func_url = self.devices_func_url
        payload = {
            "data_provider": provider,
            "token_secret_id": token_secret_id,
            "site_id": telemetry_site_id,
        }
        telemetry_response = self.post(payload=payload, use_token=True)
        self.handle_response_error(telemetry_response)
        return telemetry_response.json()

    def get_device_static_info(self, provider, token_secret_id, telemetry_site_id, telemetry_device_id):
        self.func_url = self.device_static_info_func_url
        payload = {
            "data_provider": provider,
            "token_secret_id": token_secret_id,
            "site_id": telemetry_site_id,
            "device_id": telemetry_device_id,
        }
        telemetry_response = self.post(payload=payload, use_token=True)
        self.handle_response_error(telemetry_response)
        return telemetry_response.json()
