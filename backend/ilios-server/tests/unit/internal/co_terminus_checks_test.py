import pytest

from app.settings import settings
from app.static import CoTerminusMessages
from tests.unit import samples


class TestInternalCoTerminusChecks:

    @staticmethod
    def _generate_internal_co_terminus_check_endpoint(check_id):
        return f"/api/internal/co-terminus-checks/{check_id}/results"

    @pytest.mark.parametrize(
        "api_key,expected_status_code",
        (
            (settings.api_key, 404),
            ("WRONG_API_KEY", 403),
        ),
    )
    def test_update_check_results_negative(self, client, api_key, expected_status_code):
        response = client.patch(
            self._generate_internal_co_terminus_check_endpoint(9999),
            params={"api_key": api_key},
            json={"status": "Completed", "items": []},
        )
        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "request_status,request_items",
        (
            ("Completed", samples.CO_TERM_UPDATE_RESULT_API_ITEMS),
            ("Processing Failed", []),
        ),
    )
    def test_update_check_results_success(self, client, co_terminus_check, request_status, request_items):
        response = client.patch(
            self._generate_internal_co_terminus_check_endpoint(co_terminus_check.id),
            params={"api_key": settings.api_key},
            json={"status": request_status, "items": request_items},
        )
        assert response.status_code == 202
        assert response.json()["message"] == CoTerminusMessages.check_results_save_success.value
