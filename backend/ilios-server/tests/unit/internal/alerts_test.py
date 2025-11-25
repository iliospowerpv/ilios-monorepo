from copy import deepcopy

from app.crud.alert import AlertCRUD
from app.settings import settings
from app.static import AlertMessages
from tests.unit import samples


class TestAlerts:
    INTERNAL_PATH = "/api/internal"
    ALERTS_ENDPOINT = f"{INTERNAL_PATH}/alerts"

    def test_create_device_alert(
        self,
        client,
        device_id,
    ):
        payload = deepcopy(samples.TEST_ALERT_BODY)
        payload["device_id"] = device_id
        response = client.post(
            f"{self.ALERTS_ENDPOINT}",
            params={"api_key": settings.api_key},
            json=payload,
        )
        assert response.status_code == 201
        assert response.json()["message"] == AlertMessages.alert_create_success.value

    def test_create_device_alert_duplicated(
        self,
        client,
        device_id,
        db_session,
    ):
        payload = deepcopy(samples.TEST_ALERT_BODY)
        payload["device_id"] = device_id
        payload["severity"] = "critical"
        AlertCRUD(db_session).create_item(payload)
        payload["severity"] = "Critical"
        response = client.post(
            self.ALERTS_ENDPOINT,
            params={"api_key": settings.api_key},
            json=payload,
        )
        assert response.status_code == 409
        assert response.json()["message"] == AlertMessages.alert_already_exists.value

    def test_create_device_alert_404(
        self,
        client,
    ):
        payload = deepcopy(samples.TEST_ALERT_BODY)
        payload["device_id"] = 999
        response = client.post(self.ALERTS_ENDPOINT, params={"api_key": settings.api_key}, json=payload)
        assert response.status_code == 404

    def test_create_device_alert_403(
        self,
        client,
        device_id,
    ):
        payload = deepcopy(samples.TEST_ALERT_BODY)
        payload["device_id"] = device_id
        response = client.post(
            self.ALERTS_ENDPOINT,
            params={"api_key": "invalid_key"},
            json=payload,
        )
        assert response.status_code == 403
