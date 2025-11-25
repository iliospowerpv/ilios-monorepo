from app.crud.telemetry_mapping import TelemetrySiteMappingCRUD
from app.static import TelemetryMessages
from tests.utils import create_response


class TestTelemetry:
    @staticmethod
    def _generate_sites_mapping_endpoint(_site_id):
        return f"/api/telemetry/sites/{_site_id}/mapping"

    @staticmethod
    def _generate_sites_devices_endpoint(_site_id):
        return f"/api/telemetry/sites/{_site_id}/devices"

    def test_create_telemetry_site_mapping(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        das_connection,
        mocker,
    ):
        """Test create Telemetry site mapping."""
        payload = {
            "telemetry_site_id": "8nfavWSrpi",
            "telemetry_site_name": "Pequawket Trail Baldwin",
            "site_id": site_id,
            "connection_id": das_connection.id,
        }
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        response = client.post(
            f"{self._generate_sites_mapping_endpoint(site_id)}",
            headers=company_member_user_auth_header,
            json=payload,
        )
        response_json = response.json()
        assert response.status_code == 201
        assert response_json["message"] == TelemetryMessages.site_mapping_create_success.value

    def test_create_telemetry_site_mapping_already_exists(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        das_connection,
        mocker,
        db_session,
    ):
        """Test create Telemetry site mapping if mapping already exists."""
        payload = {
            "telemetry_site_id": "8nfavWSrpi",
            "telemetry_site_name": "Pequawket Trail Baldwin",
            "site_id": site_id,
            "connection_id": das_connection.id,
        }
        TelemetrySiteMappingCRUD(db_session).create_item(payload)
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        response = client.post(
            f"{self._generate_sites_mapping_endpoint(site_id)}",
            headers=company_member_user_auth_header,
            json=payload,
        )
        response_json = response.json()
        assert response.status_code == 400
        assert response_json["message"] == TelemetryMessages.site_mapping_already_exists.value

    def test_create_telemetry_site_mapping_wrong_connection(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        das_connection,
        mocker,
        db_session,
    ):
        """Test create Telemetry site mapping with incorrect connection ID."""
        payload = {
            "telemetry_site_id": "8nfavWSrpi",
            "telemetry_site_name": "Pequawket Trail Baldwin",
            "site_id": site_id,
            "connection_id": 9999,
        }
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        response = client.post(
            f"{self._generate_sites_mapping_endpoint(site_id)}",
            headers=company_member_user_auth_header,
            json=payload,
        )
        assert response.status_code == 403

    def test_create_telemetry_site_mapping_403(
        self,
        client,
        non_system_user_auth_header,
        site_id,
        das_connection,
    ):
        """Test create Telemetry site mapping 403."""
        payload = {
            "telemetry_site_id": "8nfavWSrpi",
            "telemetry_site_name": "Pequawket Trail Baldwin",
            "site_id": site_id,
            "connection_id": das_connection.id,
        }
        response = client.post(
            f"{self._generate_sites_mapping_endpoint(site_id)}",
            headers=non_system_user_auth_header,
            json=payload,
        )
        assert response.status_code == 403

    def test_create_telemetry_site_mapping_404(
        self,
        client,
        system_user_auth_header,
        site_id,
        das_connection,
    ):
        """Test create Telemetry site mapping 403."""
        payload = {
            "telemetry_site_id": "8nfavWSrpi",
            "telemetry_site_name": "Pequawket Trail Baldwin",
            "site_id": site_id,
            "connection_id": das_connection.id,
        }
        response = client.post(
            f"{self._generate_sites_mapping_endpoint(99999)}",
            headers=system_user_auth_header,
            json=payload,
        )
        assert response.status_code == 404

    def test_get_telemetry_site_devices(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        telemetry_site_mapping,
        mocker,
    ):
        """Test get site devices list from telemetry."""
        external_device_id = "8nfavWSrpi"
        external_device_name = "Pequawket Trail Baldwin"
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = create_response(
            200, [{"id": external_device_id, "name": external_device_name}]
        )
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        response = client.get(
            self._generate_sites_devices_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        response_json = response.json()
        telemetry_device = response_json["items"][0]

        assert response.status_code == 200
        assert telemetry_device["name"] == external_device_name
        assert telemetry_device["id"] == external_device_id

    def test_get_telemetry_site_devices_no__das_connection(
        self,
        client,
        company_member_user_auth_header,
        site_id,
    ):
        """Test get site devices list from telemetry returns empty list when das connection was removed."""
        response = client.get(
            self._generate_sites_devices_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["items"] == []

    def test_get_telemetry_site_devices_403(
        self,
        client,
        non_system_user_auth_header,
        site_id,
    ):
        """Test get site devices list from telemetry returns 403."""
        response = client.get(
            self._generate_sites_devices_endpoint(site_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_telemetry_site_devices_404(
        self,
        client,
        system_user_auth_header,
        company_id,
    ):
        """Test get site devices list from telemetry returns 404."""
        response = client.get(
            self._generate_sites_devices_endpoint(9999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404
