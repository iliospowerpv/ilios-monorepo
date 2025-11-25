from unittest.mock import ANY

import tests.unit.samples as samples
from app.static import PBI_CONTENT_TYPE_HEADER, PowerBIMessages


class TestReports:

    @staticmethod
    def _gen_list_endpoint():
        return "/api/reporting/reports"

    @staticmethod
    def _gen_individual_endpoint():
        # report_id isn't validated, we're good to hardcode it here
        return "/api/reporting/reports/report_id_"

    def _gen_individual_report_with_suffix(self, suffix_name):
        return f"{self._gen_individual_endpoint()}/{suffix_name}"

    def _gen_embedding_endpoint(self):
        return self._gen_individual_report_with_suffix("generate-embedding-token")

    def _gen_pages_endpoint(self):
        return self._gen_individual_report_with_suffix("pages")

    def _gen_export_endpoint(self):
        return self._gen_individual_report_with_suffix("export-to-file")

    def _gen_individual_export_endpoint(self):
        return f"{self._gen_individual_endpoint()}/exports/export_id_"

    def _gen_export_status_endpoint(self):
        return f"{self._gen_individual_export_endpoint()}/status"

    def _gen_export_file_endpoint(self):
        return f"{self._gen_individual_export_endpoint()}/file"

    def test_get_reports_success(
        self, client, company_member_user_auth_header, pbi_token_reports_mock_200, pbi_no_cache
    ):
        """No cache, mocked success API calls"""
        response = client.get(self._gen_list_endpoint(), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json() == samples.EXPECTED_REPORTS_RESPONSE

    def test_get_reports_request_error(self, client, company_member_user_auth_header, pbi_token_mock_400, pbi_no_cache):
        """No cache, token request returns error"""
        response = client.get(self._gen_list_endpoint(), headers=company_member_user_auth_header)

        assert response.status_code == 400
        assert response.json()["message"] == PowerBIMessages.service_unavailable.value

    def test_get_reports_success_from_cache(
        self, client, company_member_user_auth_header, pbi_reports_mock_200, pbi_with_cache
    ):
        """Access token is retrieved from cache"""
        response = client.get(self._gen_list_endpoint(), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json() == samples.EXPECTED_REPORTS_RESPONSE

    def test_get_report_embed_token_success(
        self, client, company_member_user_auth_header, pbi_token_embed_mock_200, pbi_no_cache
    ):
        """No cache, mocked success API calls"""
        response = client.get(self._gen_embedding_endpoint(), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json() == samples.EXPECTED_EMBED_TOKEN_RESPONSE

    def test_get_report_embed_token_success_from_cache(self, client, company_member_user_auth_header, pbi_with_cache):
        """Both access and embed tokens are from cache"""
        response = client.get(self._gen_embedding_endpoint(), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json() == samples.EXPECTED_EMBED_TOKEN_RESPONSE_FROM_CACHE

    def test_get_report_pages_success(
        self, client, company_member_user_auth_header, pbi_generic_json_mock_200, pbi_with_cache
    ):
        response = client.get(self._gen_pages_endpoint(), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json() == samples.POWER_BI_GENERIC_RESPONSE

    def test_export_to_file_success(
        self, client, company_member_user_auth_header, pbi_generic_json_mock_200, pbi_with_cache
    ):
        response = client.post(
            self._gen_export_endpoint(), headers=company_member_user_auth_header, json=samples.PBI_EXPORT_REQUEST_BODY
        )

        assert response.status_code == 200
        assert response.json() == samples.POWER_BI_GENERIC_RESPONSE
        pbi_generic_json_mock_200.request.assert_called_once_with(
            data=None, json=samples.PBI_EXPORT_REQUEST_BODY, headers=ANY, method="POST", params=None, url=ANY
        )

    def test_export_status_success(
        self, client, company_member_user_auth_header, pbi_generic_json_mock_200, pbi_with_cache
    ):
        response = client.get(self._gen_export_status_endpoint(), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.json() == samples.POWER_BI_GENERIC_RESPONSE

    def test_export_file_success(
        self, client, company_member_user_auth_header, pbi_response_pdf_mock_200, pbi_with_cache
    ):
        response = client.get(self._gen_export_file_endpoint(), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert response.headers[PBI_CONTENT_TYPE_HEADER] == "application/pdf"
