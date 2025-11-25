import pickle
from copy import deepcopy
from datetime import datetime, timedelta

import pytest as pytest
import pytz
from pytest_lazy_fixtures import lf

from app.crud.telemetry_mapping import TelemetryDeviceMappingCRUD
from app.models.device import DeviceCategories
from app.static import DASConnectionStatus
from tests.unit import samples


class TestOmSite:

    OM_SITE_API_ENDPOINT = "/api/operations-and-maintenance/sites"

    def _gen_site_devices_endpoint(self, _site_id):
        return f"{self.OM_SITE_API_ENDPOINT}/{_site_id}/devices"

    def _gen_site_actual_production_chart_endpoint(self, _site_id):
        return f"{self.OM_SITE_API_ENDPOINT}/{_site_id}/actual-production-chart"

    def _gen_site_inverters_performance_chart_endpoint(self, _site_id):
        return f"{self.OM_SITE_API_ENDPOINT}/{_site_id}/inverters-performance-chart"

    def _gen_site_past_performance_chart_endpoint(self, _site_id):
        return f"{self.OM_SITE_API_ENDPOINT}/{_site_id}/past-performance-chart"

    def _gen_site_actual_vs_expected_chart_endpoint(self, _site_id):
        return f"{self.OM_SITE_API_ENDPOINT}/{_site_id}/actual-vs-expected-chart"

    def _gen_site_devices_overview_endpoint(self, _site_id):
        return f"{self.OM_SITE_API_ENDPOINT}/{_site_id}/devices-overview-section"

    def test_get_om_site_devices(self, client, db_session, company_member_user_auth_header, site_id, device_id):
        """Test get all site devices for O&M, the <last_reported> field test is moved separately"""
        response = client.get(
            self._gen_site_devices_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        items = response_json["items"]

        assert items[0]["id"] == device_id
        assert items[0]["name"] == samples.TEST_INVERTER_DEVICE_NAME
        assert items[0]["asset_id"] == samples.TEST_INVERTER_DEVICE_ASSET_ID
        assert items[0]["type"] == samples.TEST_INVERTER_DEVICE_TYPE
        assert items[0]["category"] == samples.TEST_INVERTER_DEVICE_CATEGORY
        assert items[0]["lifetime"] is None
        assert items[0]["warranty_period"] is None
        assert items[0]["alerts_overview"] == {"total": 0, "severity": None}
        assert items[0]["das_connection_status"] == DASConnectionStatus.not_connected.value

    @pytest.mark.parametrize(
        "device,mapping_fixture,return_cache_response,return_bq_response,timedelta_diff,expected_last_reported",
        (
            # device which is not tracked by telemetry
            (samples.TEST_MODULE_DEVICE_BODY, None, False, False, None, "N/A"),
            # device which is tracked by telemetry but not mapped
            (samples.TEST_INVERTER_DEVICE_BODY, None, False, False, None, None),
            # device which is tracked by telemetry, mapped, data is received from BQ or cache
            (
                samples.TEST_INVERTER_DEVICE_BODY,
                lf("telemetry_device_mapping"),
                False,
                True,
                timedelta(hours=3, minutes=2),
                "3 hours and 2 minutes",
            ),
            (
                samples.TEST_INVERTER_DEVICE_BODY,
                lf("telemetry_device_mapping"),
                True,
                False,
                timedelta(hours=24),
                "more than 24 hours",
            ),
        ),
        indirect=["device"],
    )
    def test_get_om_site_devices_last_reported(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        device,
        mapping_fixture,
        return_cache_response,
        return_bq_response,
        timedelta_diff,
        expected_last_reported,
        mocker,
        freezer,
    ):
        """Test get all site devices for O&M, the <last_reported> field test is moved separately"""
        cache_response = None
        bq_response = []
        if return_cache_response or return_bq_response:
            mocked_datetime_now = datetime(year=2025, month=1, day=20, hour=11, minute=12, second=32, microsecond=123)
            mocked_device_response_time = mocked_datetime_now - timedelta_diff
            freezer.move_to(mocked_datetime_now)
            device_last_reported_response = [
                {"device_id": device.id, "device_last_report_ts": mocked_device_response_time}
            ]
            if return_bq_response:
                bq_response = device_last_reported_response
            if return_cache_response:
                cache_response = pickle.dumps(device_last_reported_response)

        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = cache_response
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        telemetry_bq_engine.return_value.execute_query.return_value = bq_response

        response = client.get(
            self._gen_site_devices_endpoint(site_id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["items"][0]["last_reported"] == expected_last_reported

    def test_get_om_site_devices_empty(self, client, db_session, company_member_user_auth_header, site_id):
        """Test get all site devices for O&M, received empty items"""
        response = client.get(
            self._gen_site_devices_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10
        assert len(response_json["items"]) == 0

    def test_get_om_site_devices_403(self, client, db_session, non_system_user_auth_header, site_id):
        """Test get all site devices for O&M forbidden"""

        response = client.get(
            self._gen_site_devices_endpoint(site_id),
            headers=non_system_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 403
        assert response_json["message"] == "Forbidden"

    def test_get_site_by_id_404(self, client, system_user_auth_header, site_id):
        """Test get site by ID 404"""
        response = client.get(
            f"{self.OM_SITE_API_ENDPOINT}/{site_id + 1}",
            headers=system_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 404
        assert response_json["message"] == "Not Found"

    def test_get_site_by_id_403(self, client, non_system_user_auth_header, site_id):
        """Test get site by ID 404"""
        response = client.get(
            f"{self.OM_SITE_API_ENDPOINT}/{site_id}",
            headers=non_system_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 403
        assert response_json["message"] == "Forbidden"

    @pytest.mark.parametrize("alerts", [10], indirect=True)
    def test_get_site_by_id(
        self, client, system_user_auth_header, site_id, device_id, alerts, mocked_big_query_site_data
    ):
        """Test get site by ID"""

        response = client.get(
            f"{self.OM_SITE_API_ENDPOINT}/{site_id}",
            headers=system_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["id"] == site_id
        assert response_json["name"] == samples.TEST_SITE_NAME

    def test_get_site_actual_production_chart_capacities_floats(
        self, client, system_user_auth_header, site_id, db_session, mocked_big_query_site_actual_production_data
    ):
        """Ensure that site actual and expected capacities are rounded to 2 decimal places.

        Tests the bug https://softserve-jirasw.atlassian.net/browse/IOSP1-820
        """
        response = client.get(
            self._gen_site_actual_production_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200

        # ensure that new site float capacity is rounded and limited to 2 digits scale.
        # values are in SITE_DASHBOARD_BIGQUERY_RESPONSE:
        assert response_json["actual_kw"] == samples.TEST_BQ_ACTUAL_KW
        assert response_json["expected_kw"] == samples.TEST_BQ_EXPECTED_KW
        assert response_json["performance_index"] == samples.TEST_PERFORMANCE_INDEX

    def test_get_site_actual_production_chart(
        self, client, system_user_auth_header, site_id, db_session, mocked_big_query_site_actual_production_data
    ):
        """Test GET site actual production chart"""
        expected_response = {
            "actual_kw": samples.TEST_BQ_ACTUAL_KW,
            "expected_kw": samples.TEST_BQ_EXPECTED_KW,
            "weather": "N/A",
            "actual_vs_expected": samples.TEST_ACTUAL_VS_EXPECTED,
            "system_size_ac": samples.TEST_SITE_SYSTEM_SIZE_AC,
            "system_size_dc": samples.TEST_SITE_SYSTEM_SIZE_DC,
            "performance_index": samples.TEST_PERFORMANCE_INDEX,
        }
        expected_response.update(samples.EXPECTED_CUMULATIVE_PRODUCTION_SECTION_DETAILS)
        response = client.get(
            self._gen_site_actual_production_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json() == expected_response

    def test_get_site_actual_production_chart_cached_telemetry(
        self,
        client,
        system_user_auth_header,
        site_id,
        db_session,
        mocked_big_query_site_actual_production_data_from_cache,
    ):
        """Test get site actual dashboard chart with telemetry data stored in cache"""

        response = client.get(
            self._gen_site_actual_production_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200

        assert response_json["actual_kw"] == 42.0
        assert response_json["expected_kw"] == 13.0
        assert response_json["performance_index"] == 3.23

    @pytest.mark.parametrize(
        "is_device_mapped, is_telemetry_data_returned, expected_response",
        (
            # device mapped and BQ data returned metrics for the device, metrics are rounded to scale 2
            (True, True, samples.DEVICE_PERFORMANCE_CHART_RESPONSE_MAPPED),
            # device mapped but no BQ data returned
            (True, False, samples.DEVICE_PERFORMANCE_CHART_RESPONSE_MAPPED_NO_BQ_DATA),
            # device not mapped
            (False, False, samples.DEVICE_PERFORMANCE_CHART_RESPONSE_NOT_MAPPED),
        ),
    )
    def test_get_site_device_performance_chart(
        self,
        client,
        system_user_auth_header,
        site_id,
        device_id,
        telemetry_device_mapping,
        db_session,
        is_device_mapped,
        expected_response,
        is_telemetry_data_returned,
        mocker,
    ):
        """Validates following cases:
        1. Not mapped devices got performance as N/A,
        2. Mapped devices receive performance based on telemetry data:
            actual telemetry data if device found
            0 if BQ doesn't return telemetry data
        """
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = None
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        bq_response = deepcopy(samples.DEVICES_PERFORMANCE_DASHBOARD_BIGQUERY_RESPONSE)
        if not is_device_mapped:
            # remove device mapping object
            TelemetryDeviceMappingCRUD(db_session).delete_by_id(telemetry_device_mapping.id)
        if is_telemetry_data_returned:
            # patch BQ response to be linked to the current device
            bq_response[0]["device_id"] = device_id
        telemetry_bq_engine.return_value.execute_query.return_value = bq_response

        response = client.get(
            self._gen_site_inverters_performance_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json() == expected_response

    def test_get_site_device_performance_chart_from_cache(
        self,
        client,
        system_user_auth_header,
        site_id,
        device_id,
        telemetry_device_mapping,
        mocker,
    ):
        """Check if cache exists"""
        mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        # cache returned value for other device, doesn't linked to the current site
        cache_mock.return_value.get.return_value = pickle.dumps([{"device_id": device_id + 1, "performance": 0}])

        response = client.get(
            self._gen_site_inverters_performance_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json() == samples.DEVICE_PERFORMANCE_CHART_RESPONSE_MAPPED_NO_BQ_DATA

    def test_get_site_past_performance_chart(
        self,
        client,
        system_user_auth_header,
        site_id,
        mocker,
    ):
        """Test get site performance from telemetry bigquery"""
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = None
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        telemetry_bq_engine.return_value.execute_query.return_value = samples.TELEMETRY_SITE_PAST_PERFORMANCE_RESPONSE

        response = client.get(
            self._gen_site_past_performance_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["data"] == samples.SITE_PAST_PERFORMANCE_RESPONSE

    def test_get_site_past_performance_chart_from_cache(
        self,
        client,
        system_user_auth_header,
        site_id,
        mocker,
    ):
        """Test get site performance from cache"""
        mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = pickle.dumps({"2024-12-12T00:00:00": 0})

        response = client.get(
            self._gen_site_past_performance_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["data"] == {"2024-12-12T00:00:00": 0}

    def test_get_site_past_performance_chart_404(
        self,
        client,
        system_user_auth_header,
        site_id,
    ):
        """Test get site performance returns 404"""
        response = client.get(
            self._gen_site_past_performance_chart_endpoint(999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_get_site_actual_vs_expected_chart(
        self,
        client,
        system_user_auth_header,
        site_id,
        mocker,
    ):
        """Test get site actual, expected and irradiance from telemetry bigquery"""
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = None
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        telemetry_bq_engine.return_value.execute_query.return_value = (
            samples.TELEMETRY_SITE_ACTUAL_VS_EXPECTED_IRRADIANCE_FOR_1_DAY
        )

        response = client.get(
            self._gen_site_actual_vs_expected_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["data"] == samples.SITE_ACTUAL_VS_EXPECTED_RESPONSE

    def test_get_site_actual_vs_expected_chart_from_cache(
        self,
        client,
        system_user_auth_header,
        site_id,
        mocker,
    ):
        """Test get site actual, expected and irradiance from cache"""
        mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = pickle.dumps(
            [{"period": "2025-01-12T00:00:00", "actual": 0, "expected": 0, "irradiance": 0}]
        )

        response = client.get(
            self._gen_site_actual_vs_expected_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["data"] == [
            {"period": "2025-01-12T00:00:00", "actual": 0, "expected": 0, "irradiance": 0}
        ]

    def test_get_site_actual_vs_expected_chart_no_telemetry_data(
        self,
        client,
        system_user_auth_header,
        site_id,
        mocker,
    ):
        """Test get site actual, expected and irradiance from telemetry bigquery"""
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = None
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        telemetry_bq_engine.return_value.execute_query.return_value = []

        def gen_zero_power_response():
            site_power_actual_vs_expected_response = []
            interval_end_date = datetime.now(pytz.timezone("UTC")).date()
            interval_start_date = interval_end_date - timedelta(days=7)

            time_format = "%Y-%m-%dT%H:%M:%S"
            while interval_start_date < interval_end_date:
                period = datetime(interval_start_date.year, interval_start_date.month, interval_start_date.day, 0, 0, 0)
                for hour in range(0, 24):
                    current_period = period + timedelta(hours=hour)
                    site_power_actual_vs_expected_response.append(
                        {
                            "period": current_period.strftime(time_format),
                            "actual": 0,
                            "expected": 0,
                            "irradiance": 0,
                        }
                    )
                interval_start_date += timedelta(days=1)
            return site_power_actual_vs_expected_response

        response = client.get(
            self._gen_site_actual_vs_expected_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["data"] == gen_zero_power_response()

    def test_get_site_site_actual_vs_expected_chart_404(
        self,
        client,
        system_user_auth_header,
        site_id,
    ):
        """Test get site actual, expected and irradiance returns 404"""
        response = client.get(
            self._gen_site_actual_vs_expected_chart_endpoint(999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "device,mapping_fixture,category_name,return_cache_response,return_bq_response,timedelta_diff,"
        "expected_no_respond_count",
        (
            # device which is not tracked by telemetry
            (samples.TEST_MODULE_DEVICE_BODY, None, DeviceCategories.module.value, False, False, None, 0),
            # device which is tracked by telemetry, mapped, data is received from BQ or cache
            (
                samples.TEST_INVERTER_DEVICE_BODY,
                lf("telemetry_device_mapping"),
                DeviceCategories.inverter.value,
                False,
                True,
                timedelta(minutes=15),
                0,
            ),
            (
                samples.TEST_INVERTER_DEVICE_BODY,
                lf("telemetry_device_mapping"),
                DeviceCategories.inverter.value,
                True,
                False,
                timedelta(minutes=30),
                1,
            ),
        ),
        indirect=["device"],
    )
    def test_get_om_site_devices_overview(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        device,
        mapping_fixture,
        category_name,
        return_cache_response,
        return_bq_response,
        timedelta_diff,
        expected_no_respond_count,
        mocker,
        freezer,
    ):
        """Test devices <no respond> field is populated based on BQ response"""
        cache_response = None
        bq_response = []
        if return_cache_response or return_bq_response:
            mocked_datetime_now = datetime(year=2025, month=1, day=20, hour=11, minute=12, second=32, microsecond=123)
            mocked_device_response_time = mocked_datetime_now - timedelta_diff
            freezer.move_to(mocked_datetime_now)
            device_last_reported_response = [
                {"device_id": device.id, "device_last_report_ts": mocked_device_response_time}
            ]
            if return_bq_response:
                bq_response = device_last_reported_response
            if return_cache_response:
                cache_response = pickle.dumps(device_last_reported_response)

        expected_response_item = {
            "device_type": category_name,
            "devices": 1,
            "critical_errors": 0,
            "no_respond": expected_no_respond_count,
        }

        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = cache_response
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        telemetry_bq_engine.return_value.execute_query.return_value = bq_response

        response = client.get(
            self._gen_site_devices_overview_endpoint(site_id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 200
        assert expected_response_item in response.json()["data"]
