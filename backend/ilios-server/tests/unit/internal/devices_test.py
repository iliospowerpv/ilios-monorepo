from http.client import HTTPException

from app.models.device import DeviceStatuses
from app.settings import settings
from app.static import DeviceMessages


class TestDevicesInternalEndpoints:

    @staticmethod
    def _generate_device_deprecation_endpoint(_device_id):
        return f"/api/internal/devices/{_device_id}/deprecate"

    def test_device_deprecation_404(self, client):
        response = client.patch(self._generate_device_deprecation_endpoint(1111), params={"api_key": settings.api_key})
        assert response.status_code == 404
        assert response.json()["message"] == DeviceMessages.device_not_found.value

    def test_device_deprecation_telemetry_call_error(self, client, device_id, mocker):
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")

        telemetry_mock = mocker.patch("app.helpers.telemetry.telemetry_helper.FirestoreClient")
        telemetry_mock.return_value.get_company_config.side_effect = HTTPException(500, "FireStore Error")
        response = client.patch(
            self._generate_device_deprecation_endpoint(device_id), params={"api_key": settings.api_key}
        )
        assert response.status_code == 400
        assert response.json()["message"] == "Telemetry API call failed: (500, 'FireStore Error')"

    def test_device_deprecation_success(self, client, device, mocker, db_session):
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.telemetry.telemetry_helper.FirestoreClient")

        device_status_before_update = device.status

        response = client.patch(
            self._generate_device_deprecation_endpoint(device.id), params={"api_key": settings.api_key}
        )

        db_session.refresh(device)
        device_status_after_update = device.status

        assert response.status_code == 202
        assert response.json()["message"] == DeviceMessages.device_deleted_on_das_success.value
        assert device_status_before_update != device_status_after_update
        assert device_status_after_update == DeviceStatuses.deleted_on_das
