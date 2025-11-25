import pickle
from copy import deepcopy

import tests.unit.samples as samples


class TestInvestorDashboardSites:

    @staticmethod
    def _generate_sites_list_endpoint():
        return "/api/investor-dashboard/sites"

    def test_get_sites(self, client, site_id, company_member_user_auth_header, mocker):
        bq_response_site_actual_response = deepcopy(samples.SITE_DASHBOARD_BIGQUERY_RESPONSE)
        bq_response_site_actual_response[0].update({"site_id": site_id})
        bq_response_site_cumulative_response = deepcopy(samples.TELEMETRY_SITE_CUMULATIVE_ENERGY_RESPONSE)
        bq_response_site_cumulative_response[0].update({"site_id": site_id})
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.side_effect = [None, None]
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        telemetry_bq_engine.return_value.execute_query.side_effect = [
            bq_response_site_actual_response,
            bq_response_site_cumulative_response,
        ]

        response = client.get(self._generate_sites_list_endpoint(), headers=company_member_user_auth_header)

        assert response.json()["items"] == [
            {
                "id": site_id,
                "name": samples.TEST_SITE_NAME,
                "weather": "N/A",
                "actual_kw": samples.TEST_BQ_ACTUAL_KW,
                "expected_kw": samples.TEST_BQ_EXPECTED_KW,
                "actual_vs_expected": samples.TEST_ACTUAL_VS_EXPECTED,
                "cumulative_vs_expected": 86,
                "cumulative_7_days_vs_expected": 99,
                "cumulative_30_days_vs_expected": 97,
                "das_connection_status": "Not Connected",
            }
        ]

    def test_get_sites_cached_telemetry(self, client, site_id, company_member_user_auth_header, mocker):
        bq_response_site_actual_response = pickle.dumps(
            {site_id: (samples.TEST_BQ_ACTUAL_KW, samples.TEST_BQ_EXPECTED_KW)}
        )
        bq_response_site_cumulative_response = pickle.dumps({site_id: (86, 99, 97)})
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.side_effect = [
            bq_response_site_actual_response,
            bq_response_site_cumulative_response,
        ]
        mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")

        response = client.get(self._generate_sites_list_endpoint(), headers=company_member_user_auth_header)

        assert response.json()["items"] == [
            {
                "id": site_id,
                "name": samples.TEST_SITE_NAME,
                "weather": "N/A",
                "actual_kw": samples.TEST_BQ_ACTUAL_KW,
                "expected_kw": samples.TEST_BQ_EXPECTED_KW,
                "actual_vs_expected": samples.TEST_ACTUAL_VS_EXPECTED,
                "cumulative_vs_expected": 86,
                "cumulative_7_days_vs_expected": 99,
                "cumulative_30_days_vs_expected": 97,
                "das_connection_status": "Not Connected",
            }
        ]

    def test_get_company_sites_403(self, client, non_system_user_auth_header, company_id):
        response = client.get(self._generate_sites_list_endpoint(), headers=non_system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 403
        assert response_json["message"] == "Forbidden"

    def test_get_company_sites_empty_sites(self, client, system_user_auth_header, company_id):
        response = client.get(self._generate_sites_list_endpoint(), headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert len(response_json["items"]) == 0
