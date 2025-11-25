from datetime import datetime, timedelta

from app.helpers.telemetry.bigquery.base import BaseTelemetryBigQuery
from app.schema.common import calculate_actual_vs_expected
from app.settings import settings


class TelemetryDeviceBigQuery(BaseTelemetryBigQuery):
    def __init__(self) -> None:
        super().__init__()

    def get_devices_performance(self, devices_ids: list, timezone: str = "UTC"):
        """
        Fetch device actual and expected production details from telemetry bigquery and calculate device performance.
        """
        interval_start_time, interval_end_time = self._get_current_time_period(timezone)
        # sort IDs to be sure cache is unique per same set of devices
        devices_ids = sorted(devices_ids)
        devices_ids_str = "-".join(map(str, devices_ids))
        cache_name = f"devices-production-{devices_ids_str}-{interval_start_time}-{interval_end_time}"
        cached_data = self.get_from_cache(cache_name)
        if cached_data is not None:
            return cached_data

        bq_data = self.execute_bq_function(
            "device_power_actual_vs_expected", "device_id", devices_ids, interval_start_time, interval_end_time, timezone
        )

        devices_production_response = []
        if bq_data:
            for device_response in bq_data:
                actual_kw = device_response["device_power_actual"][0]["value"] or 0
                expected_kw = device_response["device_power_expected"][0]["value"] or 0
                devices_production_response.append(
                    {
                        "device_id": device_response["device_id"],
                        "performance": calculate_actual_vs_expected(actual_kw, expected_kw),
                        "actual": actual_kw,
                        "expected": expected_kw,
                    }
                )

        # update cache with new interval BigQuery data and expiration time 15 minutes
        self.set_cache(cache_name, devices_production_response, settings.site_dashboard_expiration_seconds)
        return devices_production_response

    def get_device_last_reported(self, devices_ids: list, timezone: str = "UTC"):
        """Retrieve detail when device data was successfully retrieved last time"""
        # define end time as last full 15m interval
        _, interval_end_time = self._get_current_time_period(timezone)
        # since we retrieve data for last day, start time is end time minus day
        interval_start_time = (datetime.strptime(interval_end_time, self.time_format) - timedelta(days=7)).strftime(
            self.time_format
        )
        # sort IDs to be sure cache is unique per same set of devices
        devices_ids = sorted(devices_ids)
        devices_ids_str = "-".join(map(str, devices_ids))
        cache_name = f"devices-last-reported-{devices_ids_str}-{interval_start_time}-{interval_end_time}"
        cached_data = self.get_from_cache(cache_name)
        if cached_data is not None:
            return cached_data

        bq_data = self.execute_bq_function(
            "device_last_report_ts", "device_id", devices_ids, interval_start_time, interval_end_time, timezone
        )

        self.set_cache(cache_name, bq_data, settings.site_dashboard_expiration_seconds)
        return bq_data

    def get_device_availability_metrics(
        self, devices_ids: list, interval_start_datetime: datetime, timezone: str = "UTC"
    ):
        """Retrieve detail when device data was successfully retrieved last time"""
        # define end time as last full 15m interval
        _, interval_end_time = self._get_current_time_period(timezone)
        interval_start_time = interval_start_datetime.strftime(self.time_format)
        # sort IDs to be sure cache is unique per same set of devices
        devices_ids = sorted(devices_ids)
        devices_ids_str = "-".join(map(str, devices_ids))
        cache_name = f"devices-availability-{devices_ids_str}-{interval_start_time}-{interval_end_time}"
        cached_data = self.get_from_cache(cache_name)
        if cached_data is not None:
            return cached_data

        bq_data = self.execute_bq_function(
            "device_availability_metrics", "device_id", devices_ids, interval_start_time, interval_end_time, timezone
        )

        self.set_cache(cache_name, bq_data, settings.site_dashboard_expiration_seconds)
        return bq_data
