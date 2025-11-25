"""Tests for companies routes in O&M module."""

import pickle
from copy import deepcopy

import pytest

import tests.unit.samples as samples
from app.models.alert import AlertSeverity
from tests.utils import remove_dynamic_fields, set_user_site_access


class TestOMCompanies:
    """Tests for companies routes."""

    COMPANIES_API_ENDPOINT = "/api/operations-and-maintenance/companies"

    def _gen_company_actual_production_chart_endpoint(self, _company_id):
        return f"{self.COMPANIES_API_ENDPOINT}/{_company_id}/actual-production-chart"

    def _gen_company_actual_vs_expected_production_chart_endpoint(self, _company_id):
        return f"{self.COMPANIES_API_ENDPOINT}/{_company_id}/actual-vs-expected-production-chart"

    def _gen_company_loses_for_a_day_chart_endpoint(self, _company_id):
        return f"{self.COMPANIES_API_ENDPOINT}/{_company_id}/loses-for-a-day-chart"

    @pytest.mark.parametrize("setup_companies", [3], indirect=True)
    def test_get_companies_system_user(
        self, client, system_user_auth_header, setup_companies, mocked_big_query_site_data
    ):
        response = client.get(
            self.COMPANIES_API_ENDPOINT, params={"skip": 0, "limit": 2}, headers=system_user_auth_header
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
                "name": "Apple Inc.",
                "total_sites": 0,
                "total_capacity": 0.0,
                "total_actual_kw": 0.0,
                "total_expected_kw": 0.0,
                "actual_vs_expected": 0,
                "alerts_overview": {"total": 0, "severity": None},
            },
            {
                "name": "Green Lantern",
                "total_sites": 0,
                "total_capacity": 0.0,
                "total_actual_kw": 0.0,
                "total_expected_kw": 0.0,
                "actual_vs_expected": 0,
                "alerts_overview": {"total": 0, "severity": None},
            },
        ]

    def test_get_companies(
        self,
        client,
        company_id,
        company_member_user_auth_header,
        setup_companies,
        mocked_big_query_site_data,
        sites_placed_in_service,
    ):
        response = client.get(
            self.COMPANIES_API_ENDPOINT, params={"skip": 0, "limit": 2}, headers=company_member_user_auth_header
        )
        response_json = response.json()
        response_items = [item for item in response_json["items"]]

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 2

        assert response_items == [
            {
                "id": company_id,
                "name": "Green Lantern",
                "total_sites": 1,
                "total_capacity": 100.0,
                "total_actual_kw": 0,
                "total_expected_kw": 0,
                "actual_vs_expected": 0,
                "alerts_overview": {"total": 0, "severity": None},
            }
        ]

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_companies_with_total_sites_info_non_system_user(
        self,
        client,
        company_id,
        site_id,
        alerts,
        company_member_user_auth_header,
        sites,
        mocked_big_query_site_data,
        sites_placed_in_service,
    ):
        """Validate user has access only to sites access was provided to even if we have more sites"""
        alert_severity = alerts[0].severity.value

        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            headers=company_member_user_auth_header,
        )
        # remove ID since it's dynamic field
        response_items = response.json()["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert response_items == [
            {
                "name": samples.TEST_COMPANY_NAME,
                "total_sites": 1,
                "total_capacity": 100,
                "total_actual_kw": 0,
                "total_expected_kw": 0,
                "alerts_overview": {"severity": alert_severity, "total": 1},
                "actual_vs_expected": 0,
            }
        ]

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_companies_with_total_sites_info_system_user(
        self, client, alerts, system_user_auth_header, sites, mocked_big_query_site_data, sites_placed_in_service
    ):
        """Validate system user has access to all 3 sites under this company"""
        alert_severity = alerts[0].severity.value

        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            headers=system_user_auth_header,
        )
        # remove ID since it's dynamic field
        response_items = response.json()["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert {
            "name": samples.TEST_COMPANY_NAME,
            "total_sites": 3,
            "total_capacity": 300,
            "total_actual_kw": 0,
            "total_expected_kw": 0,
            "alerts_overview": {"severity": alert_severity, "total": 1},
            "actual_vs_expected": 0,
        } in response_items

    def test_get_companies_w_capacities_float_system_user(
        self, client, company_id, site, alerts, system_user_auth_header, db_session, mocker, sites_placed_in_service
    ):
        """Ensure that companies total_capacity and actual and expected capacities are rounded to 2 decimal places.

        Tests the bug https://softserve-jirasw.atlassian.net/browse/IOSP1-820
        """
        # set up a site with capacity sizes in long floats
        # patch DB data
        site.system_size_ac = 7.34576501423413
        db_session.commit()
        # patch BQ response
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = None
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        bq_response = deepcopy(samples.SITE_DASHBOARD_BIGQUERY_RESPONSE)
        bq_response[0]["site_id"] = site.id
        bq_response[0]["site_power_actual"][0]["value"] = 10.34432101423413
        bq_response[0]["site_power_expected"][0]["value"] = 7.545151545151
        telemetry_bq_engine.return_value.execute_query.return_value = bq_response

        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        target_company = [item for item in response.json()["items"] if item["id"] == company_id][0]
        # ensure that site float capacity is rounded and limited to 2 digits scale
        assert target_company["total_capacity"] == 7.35
        assert target_company["total_actual_kw"] == samples.TEST_BQ_ACTUAL_KW
        assert target_company["total_expected_kw"] == samples.TEST_BQ_EXPECTED_KW

    @pytest.mark.parametrize("setup_companies", [3], indirect=True)
    def test_get_companies_ordered_by_name_system_user(
        self, client, system_user_auth_header, setup_companies, mocked_big_query_site_data
    ):
        """Test that companies GET with order_by field 'name' orders output companies by their names."""
        response = client.get(self.COMPANIES_API_ENDPOINT, params={"order_by": "name"}, headers=system_user_auth_header)
        response_json = response.json()
        items = response_json["items"]

        assert items[0]["name"] == "Apple Inc."

    def test_get_companies_ordered_by_name(
        self, client, company_member_user_auth_header, setup_companies, mocked_big_query_site_data
    ):
        """Test that companies GET with order_by field 'name' orders output companies by their names."""
        response = client.get(
            self.COMPANIES_API_ENDPOINT, params={"order_by": "name"}, headers=company_member_user_auth_header
        )
        response_json = response.json()
        items = response_json["items"]

        assert items[0]["name"] == "Green Lantern"

    def test_get_companies_no_user_sites(
        self, client, company_member_user_auth_header, setup_companies, mocker, mocked_big_query_site_data
    ):
        """Test that there are no companies when user has no sites."""
        mocker.patch("app.models.user.User.get_limited_companies_ids", return_value=[])
        response = client.get(
            self.COMPANIES_API_ENDPOINT, params={"order_by": "name"}, headers=company_member_user_auth_header
        )
        response_json = response.json()
        items = response_json["items"]

        assert len(items) == 0

    def test_get_company_sites(self, client, company_id, site_id, company_member_user_auth_header, mocker):
        """Test that get company sites return list of sites if access was provided."""
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
        response = client.get(
            f"{self.COMPANIES_API_ENDPOINT}/{company_id}/sites", headers=company_member_user_auth_header
        )
        response_json = response.json()

        items = response_json["items"]
        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert len(items) == 1
        assert items[0]["id"] == site_id
        assert items[0]["name"] == samples.TEST_SITE_NAME
        assert items[0]["weather"] == "N/A"

        assert items[0]["actual_kw"] == samples.TEST_BQ_ACTUAL_KW
        assert items[0]["expected_kw"] == samples.TEST_BQ_EXPECTED_KW
        assert items[0]["actual_vs_expected"] == samples.TEST_ACTUAL_VS_EXPECTED

        assert items[0]["cumulative_vs_expected"] == 86
        assert items[0]["cumulative_7_days_vs_expected"] == 99
        assert items[0]["cumulative_30_days_vs_expected"] == 97
        assert items[0]["alerts_overview"] == {"total": 0, "severity": None}
        assert items[0]["das_connection_status"] == "Not Connected"

    def test_get_company_sites_cached_telemetry(
        self, client, company_id, site_id, company_member_user_auth_header, mocker
    ):
        """Test that get company sites return list of sites with cached data from telemetry if access was provided."""
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
        response = client.get(
            f"{self.COMPANIES_API_ENDPOINT}/{company_id}/sites", headers=company_member_user_auth_header
        )
        response_json = response.json()

        items = response_json["items"]
        assert items[0]["actual_kw"] == samples.TEST_BQ_ACTUAL_KW
        assert items[0]["expected_kw"] == samples.TEST_BQ_EXPECTED_KW
        assert items[0]["actual_vs_expected"] == samples.TEST_ACTUAL_VS_EXPECTED

        assert items[0]["cumulative_vs_expected"] == 86
        assert items[0]["cumulative_7_days_vs_expected"] == 99
        assert items[0]["cumulative_30_days_vs_expected"] == 97

    def test_get_company_sites_403(self, client, non_system_user_auth_header, company_id):
        """Test that user with no sites access receives forbidden."""
        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}/sites", headers=non_system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 403
        assert response_json["message"] == "Forbidden"

    def test_get_company_sites_empty_sites(self, client, system_user_auth_header, company_id):
        """Test that items list is empty for non-existing company."""
        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}/sites", headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert len(response_json["items"]) == 0

    def test_get_company_by_id_404(self, client, system_user_auth_header, company_id):
        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id+1}", headers=system_user_auth_header)

        assert response.status_code == 404

    def test_get_company_by_id_403(self, client, non_system_user_auth_header, company_id):
        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}", headers=non_system_user_auth_header)

        assert response.status_code == 403

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_company_by_id_non_system_user(
        self,
        client,
        company_member_user_auth_header,
        company,
        alerts,
        sites,
        site_om_task,
        db_session,
        mocked_big_query_site_data,
    ):
        """Validate non system user has access to company sites limited by user.project_access property"""
        company_id = company.id
        test_alert = alerts[0]
        alert_severity = test_alert.severity.value
        alert_type = test_alert.type

        # link alert to the task to validate it's tracked on the dashboard
        site_om_task.alert_id = test_alert.id
        db_session.commit()

        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}", headers=company_member_user_auth_header)
        response_json = response.json()

        # remove dynamic fields from alerts section
        alerts_section = response_json["alerts_section"]
        remove_dynamic_fields(alerts_section)
        remove_dynamic_fields(alerts_section, field_name="alert_start")
        remove_dynamic_fields(alerts_section, field_name="alert_end")

        assert response.status_code == 200
        assert response_json["id"] == company_id
        assert response_json["name"] == samples.TEST_COMPANY_NAME

        assert {"severity": alert_severity, "type": alert_type} in alerts_section
        alerts_summary_section = response_json["alerts_summary_section"]
        assert {"severity": alert_severity, "total": 1, "unaccomplished_tasks_count": 1} in alerts_summary_section

        # ensure alert severities order is alphabetical
        assert alerts_summary_section[0]["severity"] == AlertSeverity.critical.value
        assert alerts_summary_section[1]["severity"] == AlertSeverity.warning.value
        assert alerts_summary_section[2]["severity"] == AlertSeverity.informational.value

        # validate company has more sites that returned to user, meaning user received only sites user has access to
        assert len(company.sites) == 3

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_company_by_id_system_user(
        self, client, system_user_auth_header, company, sites, mocked_big_query_site_data
    ):
        """Validate system user has access to all company sites"""
        company_id = company.id
        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}", headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["id"] == company_id
        assert response_json["name"] == samples.TEST_COMPANY_NAME

        # ensure alert severities order is alphabetical
        alerts_summary_section = response_json["alerts_summary_section"]
        assert alerts_summary_section[0]["severity"] == AlertSeverity.critical.value
        assert alerts_summary_section[1]["severity"] == AlertSeverity.warning.value
        assert alerts_summary_section[2]["severity"] == AlertSeverity.informational.value

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_company_actual_production_chart(
        self,
        client,
        company_member_user_auth_header,
        company,
        sites,
        mocked_big_query_site_actual_production_data,
        db_session,
        company_member_user,
        sites_placed_in_service,
    ):
        """Validate system user has access to all company sites"""
        # provide user access for all 3 sites
        for site in sites:
            set_user_site_access(db_session, site, company_member_user)
        company_id = company.id
        expected_payload = {
            # company values
            "id": company_id,
            # knows site values: defaults, values from site creation
            "total_sites": 3,
            "total_actual_kw": samples.TEST_BQ_ACTUAL_KW,
            "total_expected_kw": samples.TEST_BQ_EXPECTED_KW,
            "total_system_size_ac": samples.TEST_SITE_SYSTEM_SIZE_AC * 3,
            "total_system_size_dc": samples.TEST_SITE_SYSTEM_SIZE_DC * 3,
            # calculated site values
            "actual_vs_expected": samples.TEST_ACTUAL_VS_EXPECTED,
        }
        expected_payload.update(samples.EXPECTED_CUMULATIVE_PRODUCTION_SECTION_DETAILS)
        response = client.get(
            self._gen_company_actual_production_chart_endpoint(company_id), headers=company_member_user_auth_header
        )

        assert response.status_code == 200
        assert response.json() == expected_payload

    def test_get_company_actual_production_chart_from_cache(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        site_id,
        mocked_big_query_site_actual_production_data_from_cache,
        db_session,
        company_member_user,
        sites_placed_in_service,
    ):
        expected_payload = {
            "id": company_id,
            "total_sites": 1,
            "total_actual_kw": 42,
            "total_expected_kw": 13,
            "total_system_size_ac": samples.TEST_SITE_SYSTEM_SIZE_AC,
            "total_system_size_dc": samples.TEST_SITE_SYSTEM_SIZE_DC,
            "actual_vs_expected": 323,
        }
        expected_payload.update(samples.EXPECTED_CUMULATIVE_PRODUCTION_SECTION_CACHED_DETAILS)
        response = client.get(
            self._gen_company_actual_production_chart_endpoint(company_id), headers=company_member_user_auth_header
        )

        assert response.status_code == 200
        assert response.json() == expected_payload

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_company_actual_vs_expected_production_chart(
        self,
        client,
        company_member_user_auth_header,
        company,
        sites,
        mocked_big_query_company_site,
        db_session,
        company_member_user,
    ):
        """Validate system user has access to all company sites"""
        # provide user access for all 3 sites
        for site in sites:
            set_user_site_access(db_session, site, company_member_user)
        company_id = company.id
        response = client.get(
            self._gen_company_actual_vs_expected_production_chart_endpoint(company_id),
            headers=company_member_user_auth_header,
        )
        # remove site ids from items response since they are dynamic
        items = [{k: v for k, v in site_dict.items() if k != "id"} for site_dict in response.json()["items"]]
        assert response.status_code == 200
        assert items == [
            {
                "name": "Windmills Farm",
                "actual_kw": samples.TEST_BQ_ACTUAL_KW,
                "expected_kw": samples.TEST_BQ_EXPECTED_KW,
                "size": 1.0,
            },
            {"name": "Windmills Farm", "actual_kw": 0.0, "expected_kw": 0.0, "size": 1.0},
            {"name": "Windmills Farm", "actual_kw": 0.0, "expected_kw": 0.0, "size": 1.0},
        ]

    def test_get_company_by_id_w_floats_system_user(
        self,
        client,
        system_user_auth_header,
        company_id,
        site,
        db_session,
        mocked_big_query_site_actual_production_data,
        sites_placed_in_service,
    ):
        """Ensure that total_capacity and actual and expected capacities of company are rounded to 2 decimal places.

        New site is created and System user has access to all sites around company.
        Tests the bug https://softserve-jirasw.atlassian.net/browse/IOSP1-820
        """
        # set up a site with capacity sizes in long floats
        site.system_size_ac = 10.34932101423413
        site.system_size_dc = 7.54415154545151
        db_session.commit()

        response = client.get(
            self._gen_company_actual_production_chart_endpoint(company_id), headers=system_user_auth_header
        )
        response_json = response.json()

        # ensure site float values are rounded and limited to 2 digits scale
        assert response_json["total_system_size_ac"] == 10.35
        assert response_json["total_system_size_dc"] == 7.54

        assert response_json["total_actual_kw"] == samples.TEST_BQ_ACTUAL_KW
        assert response_json["total_expected_kw"] == samples.TEST_BQ_EXPECTED_KW

    def test_get_company_by_id_w_round(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        site,
        db_session,
        mocked_big_query_site_actual_production_data,
    ):
        """Ensure that actual vs expected ratio rounds value appropriately.

        Tests the bug https://softserve-jirasw.atlassian.net/browse/IOSP1-862
        """
        response = client.get(
            self._gen_company_actual_production_chart_endpoint(company_id), headers=company_member_user_auth_header
        )
        response_json = response.json()
        # test that actual_vs_expected ratio is calculated appropriately (10.341/7.551*100=136.94) and is rounded to 137
        assert response_json["actual_vs_expected"] == samples.TEST_ACTUAL_VS_EXPECTED

    @pytest.mark.parametrize(
        "bq_response, expected_response",
        (
            # if expected bigger than actual losses happens
            (
                samples.COMPANY_LOSSES_FOR_A_DAY_BQ_RESPONSE_EXPECTED_BIGGER_THAN_ACTUAL,
                samples.COMPANY_LOSSES_FOR_A_DAY_CHART_RESPONSE_WITH_LOSES,
            ),
            # if smaller or equal - no losses
            (
                samples.COMPANY_LOSSES_FOR_A_DAY_BQ_RESPONSE_EXPECTED_SMALLER_THAN_ACTUAL,
                samples.COMPANY_LOSSES_FOR_A_DAY_CHART_RESPONSE_NO_LOSES,
            ),
            (
                samples.COMPANY_LOSSES_FOR_A_DAY_BQ_RESPONSE_EXPECTED_EQUAL_ACTUAL,
                samples.COMPANY_LOSSES_FOR_A_DAY_CHART_RESPONSE_NO_LOSES_EQUAL,
            ),
        ),
    )
    def test_get_company_loses_for_a_day_chart(
        self,
        client,
        company_member_user_auth_header,
        company_id,
        mocker,
        bq_response,
        expected_response,
    ):
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = None
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        telemetry_bq_engine.return_value.execute_query.return_value = bq_response
        response = client.get(
            self._gen_company_loses_for_a_day_chart_endpoint(company_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json() == expected_response

    def test_get_company_loses_for_a_day_chart_from_cache(
        self,
        client,
        system_user_auth_header,
        company_id,
        mocker,
    ):
        mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = pickle.dumps(
            samples.COMPANY_LOSSES_FOR_A_DAY_CHART_RESPONSE_WITH_LOSES
        )
        response = client.get(
            self._gen_company_loses_for_a_day_chart_endpoint(company_id),
            headers=system_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json() == samples.COMPANY_LOSSES_FOR_A_DAY_CHART_RESPONSE_WITH_LOSES
