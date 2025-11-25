import json
import os

import pytest

from app.settings import settings


class TestInternalFiles:

    INTERNAL_PATH = "/api/internal"

    def _generate_files_endpoint(self, file_id):
        return f"{self.INTERNAL_PATH}/files/{file_id}/parsing"

    @staticmethod
    def _get_parsing_result():
        """Return payload from json"""
        json_file_path = os.path.join(os.path.dirname(__file__), "../samples/site_lease_ai_response.json")
        with open(json_file_path) as file_sample:
            data = json.load(file_sample)
        return data

    def test_update_file_parsing_results(self, client, ai_result):
        response = client.put(
            self._generate_files_endpoint(ai_result.id),
            params={"api_key": settings.api_key},
            json=self._get_parsing_result(),
        )
        assert response.status_code == 202
        assert response.json()["message"] == "File parsing results has been stored"

    @pytest.mark.parametrize(
        "api_key, expected_status_code",
        (
            (settings.api_key, 404),
            ("WRONG_API_KEY", 403),
        ),
    )
    def test_update_file_parsing_results_negative(self, client, api_key, expected_status_code):
        """Test negative cases are caught and handled appropriately"""
        response = client.put(
            self._generate_files_endpoint(9999),
            params={"api_key": api_key},
            json=self._get_parsing_result(),
        )
        assert response.status_code == expected_status_code
