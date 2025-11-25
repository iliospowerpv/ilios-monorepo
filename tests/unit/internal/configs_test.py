import pytest

from app.settings import settings
import tests.unit.samples as samples


class TestConfigManagement:
    CONFIGS_API_ENDPOINT = "/api/internal/configs"

    @pytest.mark.parametrize(
        "request_method,params,expected_status_code,expected_error",
        (
            # auth doesn't provide
            ("get", {"api_key": "WRONG_API_KEY"}, 403, "Forbidden"),
            ("put", {"api_key": "WRONG_API_KEY"}, 403, "Forbidden"),
            # config isn't defined
            ("get", {"api_key": settings.api_key}, 422, samples.CONFIG_MISSING_QUERY_ERR),
            (
                "put",
                {"api_key": settings.api_key},
                422,
                samples.CONFIG_MISSING_QUERY_AND_BODY_ERR,
            ),
            # unexpected config type
            (
                "get",
                {"api_key": settings.api_key, "config_type": "test"},
                422,
                samples.CONFIG_INVALID_QUERY_GET_ERR,
            ),
            (
                "put",
                {"api_key": settings.api_key, "config_type": "test"},
                422,
                samples.CONFIG_INVALID_QUERY_PUT_ERR,
            ),
        ),
    )
    def test_manage_config_negative(self, client, request_method, params, expected_status_code, expected_error):
        """Test get/post operations for the common errors"""

        response = client.request(method=request_method, url=self.CONFIGS_API_ENDPOINT, params=params)
        assert response.status_code == expected_status_code
        assert response.json()["message"] == expected_error

    def test_retrieve_ai_parsing_config_ok(self, client, set_test_ai_parsing_config):

        response = client.get(
            self.CONFIGS_API_ENDPOINT, params={"api_key": settings.api_key, "config_type": "ai_parsing"}
        )
        assert response.status_code == 200
        assert response.json() == {
            "Site Lease": ["Lessor (Landlord) Entity Name", "Lessee (Tenant) Entity Name", "Effective Date"]
        }

    def test_retrieve_ai_parsing_config_ok_no_file(self, client, unset_ai_parsing_config):

        response = client.get(
            self.CONFIGS_API_ENDPOINT, params={"api_key": settings.api_key, "config_type": "ai_parsing"}
        )
        assert response.status_code == 200
        assert response.json() is None

    def test_set_ai_parsing_config_ok(self, client, unset_ai_parsing_config):
        test_payload = {"test": "payload"}
        get_response_unset = client.get(
            self.CONFIGS_API_ENDPOINT, params={"api_key": settings.api_key, "config_type": "ai_parsing"}
        )

        response = client.put(
            self.CONFIGS_API_ENDPOINT,
            params={"api_key": settings.api_key, "config_type": "ai_parsing"},
            json=test_payload,
        )

        get_response_set = client.get(
            self.CONFIGS_API_ENDPOINT, params={"api_key": settings.api_key, "config_type": "ai_parsing"}
        )
        assert get_response_unset.json() is None
        assert response.status_code == 200
        assert response.json()["message"] == "Updated the 'ai_parsing' config"
        assert get_response_set.json() == test_payload
