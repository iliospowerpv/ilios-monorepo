import copy
from unittest.mock import MagicMock

import pytest

from app.crud.das_connection import DASConnectionCRUD
from app.models.telemetry import DASProvidersEnum
from app.static import TelemetryMessages
from tests.unit import samples
from tests.utils import create_response


class TestDASConnection:
    @staticmethod
    def _generate_list_endpoint(company_id_):
        return f"/api/contractors/{company_id_}/connections"

    @staticmethod
    def _generate_connection_endpoint(company_id_, connection_id_):
        return f"/api/contractors/{company_id_}/connections/{connection_id_}"

    def _generate_connection_sites_endpoint(self, company_id_, connection_id_):
        return f"{self._generate_connection_endpoint(company_id_, connection_id_)}/sites"

    @pytest.mark.parametrize(
        "payload",
        (
            samples.TEST_KMC_DAS_CONNECTION_PAYLOAD,
            samples.TEST_AE_DAS_CONNECTION_PAYLOAD,
        ),
    )
    def test_create_new_das_connection(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        mocker,
        response_200,
        payload,
    ):
        """Test create new DAS connection, check all possible data providers"""
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        firestore_mock = mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        fs_document_mock = firestore_mock.return_value.collection.return_value.document
        set_document_mock = fs_document_mock.return_value.set
        get_document_mock = fs_document_mock.return_value.get
        fs_document_mock.return_value.get.return_value.to_dict = MagicMock(return_value=None)

        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = response_200
        mock_requests = mocker.patch("app.helpers.telemetry.secrets_manager.SecretManagerServiceClient")
        mock_requests.return_value.create_secret.return_value = MagicMock(name="telemetry-secret")
        response = client.post(
            self._generate_list_endpoint(company_id),
            headers=company_member_user_auth_header,
            json=payload,
        )
        response_json = response.json()

        assert response.status_code == 201
        assert response_json["message"] == TelemetryMessages.connection_create_success.value
        assert set_document_mock.call_count == 1
        assert get_document_mock.call_count == 1

    def test_create_new_das_connection_firestore_config_update(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        mocker,
        response_200,
    ):
        """Test create new DAS connection."""
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        firestore_mock = mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        fs_document_mock = firestore_mock.return_value.collection.return_value.document
        set_document_mock = fs_document_mock.return_value.set
        get_document_mock = fs_document_mock.return_value.get

        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = response_200
        mock_requests = mocker.patch("app.helpers.telemetry.secrets_manager.SecretManagerServiceClient")
        mock_requests.return_value.create_secret.return_value = MagicMock(name="telemetry-secret")
        response = client.post(
            self._generate_list_endpoint(company_id),
            headers=company_member_user_auth_header,
            json=samples.TEST_KMC_DAS_CONNECTION_PAYLOAD,
        )
        response_json = response.json()

        assert response.status_code == 201
        assert response_json["message"] == TelemetryMessages.connection_create_success.value
        assert set_document_mock.call_count == 1
        assert get_document_mock.call_count == 1

    def test_create_new_das_connection_unique_name_err(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
        db_session,
    ):
        """Test create new DAS connection with connection name that already exists."""
        response = client.post(
            self._generate_list_endpoint(company_id),
            headers=company_member_user_auth_header,
            json=samples.TEST_KMC_DAS_CONNECTION_PAYLOAD,
        )
        response_json = response.json()

        assert response.status_code == 400
        assert response_json["message"] == TelemetryMessages.connection_name_already_exists.value

    def test_create_new_das_connection_token_validation_failed(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        mocker,
        response_400,
    ):
        """Test create new DAS connection with invalid token value."""
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = response_400
        mock_requests = mocker.patch("app.helpers.telemetry.secrets_manager.SecretManagerServiceClient")
        mock_requests.return_value.create_secret.return_value = MagicMock(name="telemetry-secret")
        response = client.post(
            self._generate_list_endpoint(company_id),
            headers=company_member_user_auth_header,
            json=samples.TEST_KMC_DAS_CONNECTION_PAYLOAD,
        )
        response_json = response.json()

        assert response.status_code == 400
        assert response_json["message"] == TelemetryMessages.token_validation_failed.value

    def test_create_new_das_connection_403(self, client, non_system_user_auth_header, company_id):
        """Test create new DAS connection 403."""
        response = client.post(
            self._generate_list_endpoint(company_id),
            headers=non_system_user_auth_header,
            json=samples.TEST_KMC_DAS_CONNECTION_PAYLOAD,
        )
        assert response.status_code == 403

    def test_create_new_das_connection_404(self, client, system_user_auth_header):
        """Test create new DAS connection 404."""
        response = client.post(
            self._generate_list_endpoint(9999),
            headers=system_user_auth_header,
            json=samples.TEST_KMC_DAS_CONNECTION_PAYLOAD,
        )
        assert response.status_code == 404

    def test_get_company_connections(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
    ):
        """Test get list of company DAS connections."""
        response = client.get(
            self._generate_list_endpoint(company_id),
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["items"][0]["id"] == das_connection.id
        assert response_json["items"][0]["name"] == samples.TEST_KMC_DAS_CONNECTION_PAYLOAD["name"]
        assert response_json["items"][0]["provider"] == DASProvidersEnum.kmc.value

    def test_get_company_connections_403(self, client, non_system_user_auth_header, company_id):
        """Test get list of company DAS connections 403."""
        response = client.get(
            self._generate_list_endpoint(company_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_company_connections_404(self, client, system_user_auth_header):
        """Test get list of company DAS connections 404."""
        response = client.get(
            self._generate_list_endpoint(9999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_update_connection_name_changed(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
        db_session,
    ):
        """Test update company connection name success."""
        response = client.put(
            self._generate_connection_endpoint(company_id, das_connection.id),
            headers=company_member_user_auth_header,
            json={"name": "New connection name", "token": None},
        )
        response_json = response.json()
        db_session.refresh(das_connection)
        assert response.status_code == 202
        assert response_json["message"] == TelemetryMessages.connection_update_success.value
        assert das_connection.name == "New connection name"

    @pytest.mark.parametrize(
        "das_connection,payload",
        (
            (DASProvidersEnum.kmc, samples.TEST_KMC_DAS_CONNECTION_PAYLOAD),
            (DASProvidersEnum.also_energy, samples.TEST_AE_DAS_CONNECTION_PAYLOAD),
        ),
        indirect=["das_connection"],
    )
    def test_update_connection_creds_changed(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
        mocker,
        response_200,
        payload,
    ):
        """Test update company connection credentials success."""
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mock_requests = mocker.patch(
            "app.helpers.telemetry.secrets_manager.SecretManagerServiceClient.add_secret_version"
        )
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = response_200
        response = client.put(
            self._generate_connection_endpoint(company_id, das_connection.id),
            headers=company_member_user_auth_header,
            json=payload,
        )
        response_json = response.json()

        assert response.status_code == 202
        assert response_json["message"] == TelemetryMessages.connection_update_success.value
        assert mock_requests.call_count == 1

    def test_update_connection_token_validation_failed(
        self, client, company_member_user_auth_header, company_id, das_connection, mocker, response_400
    ):
        """Test update company connection token with invalid token value."""
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mocker.patch("app.helpers.telemetry.secrets_manager.SecretManagerServiceClient.add_secret_version")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = response_400
        response = client.put(
            self._generate_connection_endpoint(company_id, das_connection.id),
            headers=company_member_user_auth_header,
            json={"name": das_connection.name, "token": "New token"},
        )
        response_json = response.json()

        assert response.status_code == 400
        assert response_json["message"] == TelemetryMessages.token_validation_failed.value

    def test_update_connection_403(
        self,
        client,
        non_system_user_auth_header,
        company_id,
        das_connection,
    ):
        """Test update company connection 403."""
        response = client.put(
            self._generate_connection_endpoint(company_id, das_connection.id),
            headers=non_system_user_auth_header,
            json={"name": das_connection.name, "token": "New token"},
        )
        assert response.status_code == 403

    def test_update_connection_404(
        self,
        client,
        system_user_auth_header,
        company_id,
    ):
        """Test update company connection 404."""
        response = client.put(
            self._generate_connection_endpoint(company_id, 9999),
            headers=system_user_auth_header,
            json={"name": "New name", "token": "New token"},
        )
        assert response.status_code == 404

    def test_update_connection_name_already_exists(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
        db_session,
    ):
        """Test update company connection name success."""
        duplicated_name = "Duplicated connection name"
        das_connection_record = {
            "company_id": company_id,
            "name": duplicated_name,
            "provider": DASProvidersEnum.also_energy,
            "secret_token_name": "test_token",
        }
        DASConnectionCRUD(db_session).create_item(das_connection_record)
        response = client.put(
            self._generate_connection_endpoint(company_id, das_connection.id),
            headers=company_member_user_auth_header,
            json={"name": duplicated_name, "token": None},
        )
        response_json = response.json()

        assert response.status_code == 400
        assert response_json["message"] == TelemetryMessages.connection_name_already_exists.value

    def test_delete_connection(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
        mocker,
        fs_company_config,
    ):
        """Test hard delete company connection success."""
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        firestore_mock = mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        firestore_delete_mock = firestore_mock.return_value.collection.return_value.document.return_value.delete
        firestore_mock.return_value.collection.return_value.document.return_value.get.return_value = fs_company_config

        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        delete_secret_mock = mocker.patch(
            "app.helpers.telemetry.secrets_manager.SecretManagerServiceClient.delete_secret"
        )
        response = client.delete(
            self._generate_connection_endpoint(company_id, das_connection.id),
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["message"] == TelemetryMessages.connection_delete_success.value
        assert delete_secret_mock.call_count == 1
        assert firestore_delete_mock.call_count == 1

    def test_delete_connection_403(
        self,
        client,
        non_system_user_auth_header,
        company_id,
        das_connection,
    ):
        """Test delete company connection 403."""
        response = client.delete(
            self._generate_connection_endpoint(company_id, das_connection.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_delete_connection_404(
        self,
        client,
        system_user_auth_header,
        company_id,
    ):
        """Test delete company connection 404."""
        response = client.delete(
            self._generate_connection_endpoint(company_id, 9999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_get_connection_sites(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
        mocker,
    ):
        """Test get connection sites list from telemetry."""
        external_site_id = "8nfavWSrpi"
        external_site_name = "Pequawket Trail Baldwin"
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = create_response(
            200, [{"id": external_site_id, "name": external_site_name}]
        )
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        response = client.get(
            self._generate_connection_sites_endpoint(company_id, das_connection.id),
            headers=company_member_user_auth_header,
        )
        response_json = response.json()
        connection_site = response_json["items"][0]

        assert response.status_code == 200
        assert connection_site["name"] == external_site_name
        assert connection_site["id"] == external_site_id

    def test_get_connection_sites_403(
        self,
        client,
        non_system_user_auth_header,
        company_id,
        das_connection,
    ):
        """Test get connection sites list from telemetry returns 403."""
        response = client.get(
            self._generate_connection_sites_endpoint(company_id, das_connection.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_connection_sites_404(
        self,
        client,
        system_user_auth_header,
        company_id,
        das_connection,
    ):
        """Test get connection sites list from telemetry returns 404."""
        response = client.get(
            self._generate_connection_sites_endpoint(company_id, 9999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "method,name_field,expected_error",
        (
            # name is shorter than 2 characters
            ("post", "i", samples.DAS_CONNECTION_NAME_TO_SMALL_ERR),
            ("put", "i", samples.DAS_CONNECTION_NAME_TO_SMALL_ERR),
            # name is longer than 100 characters
            ("post", "i" * 111, samples.DAS_CONNECTION_NAME_TO_BIG_ERR),
            ("put", "i" * 111, samples.DAS_CONNECTION_NAME_TO_BIG_ERR),
        ),
    )
    def test_validate_das_connection_name_len(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
        db_session,
        method,
        name_field,
        expected_error,
    ):
        """Test das connection name len limitation on create/edit"""
        method_metadata = {
            "post": {
                "url": self._generate_list_endpoint(company_id),
                "payload_source": samples.TEST_KMC_DAS_CONNECTION_PAYLOAD,
            },
            "put": {
                "url": self._generate_connection_endpoint(company_id, das_connection.id),
                "payload_source": {"name": None, "token": None},
            },
        }
        request_url = method_metadata[method]["url"]
        payload_source = method_metadata[method]["payload_source"]

        payload = copy.deepcopy(payload_source)
        payload["name"] = name_field
        response = client.request(method=method, url=request_url, headers=company_member_user_auth_header, json=payload)

        assert response.status_code == 422
        assert response.json()["message"] == expected_error

    @pytest.mark.parametrize(
        "payload,expected_error",
        (
            # kmc
            (
                samples.TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_FIELD,
                samples.TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_ERR,
            ),
            (
                samples.TEST_KMC_DAS_CONNECTION_PAYLOAD_EMPTY_TOKEN_FIELD,
                samples.TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_ERR,
            ),
            (
                samples.TEST_KMC_DAS_CONNECTION_PAYLOAD_EMPTY_STRING_TOKEN_FIELD,
                samples.TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_ERR,
            ),
            # also energy
            (
                samples.TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_FIELDS,
                samples.TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_ERR,
            ),
            (
                samples.TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_USERNAME_FIELD,
                samples.TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_ERR,
            ),
            (
                samples.TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_PASSWORD_FIELD,
                samples.TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_ERR,
            ),
        ),
    )
    def test_create_connection_credentials_validation_error(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        payload,
        expected_error,
    ):
        """Test credentials provided based on the DAS provider type"""
        response = client.post(
            self._generate_list_endpoint(company_id),
            headers=company_member_user_auth_header,
            json=payload,
        )
        response_json = response.json()

        assert response.status_code == 422
        assert response_json["message"] == expected_error

    def test_get_connection_sites_telemetry_error(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        das_connection,
        mocker,
    ):
        """Test get connection sites list return user-friendly error if telemetry call fails"""
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = create_response(401, {})
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        response = client.get(
            self._generate_connection_sites_endpoint(company_id, das_connection.id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 400
        assert response.json()["message"] == TelemetryMessages.das_provider_unavailable.value
