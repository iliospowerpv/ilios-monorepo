import pytest

import tests.unit.samples as samples
from tests.utils import remove_dynamic_fields


class TestInvestorDashboardCompanies:

    @staticmethod
    def _generate_generic_endpoint(entity_name_):
        return f"/api/investor-dashboard/{entity_name_}"

    def _generate_companies_list_endpoint(self):
        return self._generate_generic_endpoint("companies")

    def _generate_company_actual_production_endpoint(self, company_id_):
        return f"{self._generate_companies_list_endpoint()}/{company_id_}/actual-production"

    def test_get_companies(
        self, client, company_member_user_auth_header, sites_placed_in_service, mocked_big_query_site_data
    ):
        response = client.get(
            self._generate_companies_list_endpoint(),
            params={"skip": 0, "limit": 2},
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        # remove ID since it's dynamic field
        response_items = response_json["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 2

        assert response_items == [
            {
                "name": "Green Lantern",
                "total_sites": 1,
                "total_capacity": 100.0,
                "total_actual_kw": 0,
                "total_expected_kw": 0,
                "actual_vs_expected": 0,
            },
        ]

    def test_get_companies_without_proper_access(self, client, non_system_user_auth_header):
        response = client.get(self._generate_companies_list_endpoint(), headers=non_system_user_auth_header)

        assert response.status_code == 403

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_company_actual_production(
        self,
        client,
        company_member_user_auth_header,
        company,
        alerts,
        sites,
        mocked_big_query_site_actual_production_data,
        sites_placed_in_service,
    ):
        """Validate non system user has access to company sites limited by user.project_access property"""
        expected_payload = {
            "id": company.id,
            "total_sites": 1,
            "total_actual_kw": samples.TEST_BQ_ACTUAL_KW,
            "total_expected_kw": samples.TEST_BQ_EXPECTED_KW,
            "total_system_size_ac": samples.TEST_SITE_SYSTEM_SIZE_AC,
            "total_system_size_dc": samples.TEST_SITE_SYSTEM_SIZE_DC,
            "actual_vs_expected": samples.TEST_ACTUAL_VS_EXPECTED,
        }
        expected_payload.update(samples.EXPECTED_CUMULATIVE_PRODUCTION_SECTION_DETAILS)
        response = client.get(
            self._generate_company_actual_production_endpoint(company.id), headers=company_member_user_auth_header
        )

        assert response.status_code == 200
        assert response.json() == expected_payload

    def test_get_company_actual_production_without_proper_access(self, client, company_id, non_system_user_auth_header):
        response = client.get(
            self._generate_company_actual_production_endpoint(company_id), headers=non_system_user_auth_header
        )

        assert response.status_code == 403
