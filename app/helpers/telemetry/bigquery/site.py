from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone

import pytz

from app.helpers.telemetry.bigquery.base import BaseTelemetryBigQuery
from app.schema.common import calculate_actual_vs_expected
from app.settings import settings


class TelemetrySiteBigQuery(BaseTelemetryBigQuery):
    def __init__(self) -> None:
        super().__init__()

    def _get_site_cumulative_data(self, site_ids: list, interval_start: str, interval_end: str, timezone: str):
        object_ids = ", ".join(map(str, site_ids))
        query = (
            f"SELECT   site_id,"
            "(SELECT SUM(point_data.value) FROM UNNEST(ARRAY_SLICE(site_energy_actual, 30, 30)) AS point_data) "
            "AS site_energy_actual_today,"
            "(SELECT SUM(point_data.value) FROM UNNEST(ARRAY_SLICE(site_energy_expected, 30, 30)) AS point_data) "
            "AS site_energy_expected_today,"
            "(SELECT SUM(point_data.value) FROM UNNEST(ARRAY_SLICE(site_energy_actual, 23, 29)) AS point_data) "
            "AS site_energy_actual_last_7_days,"
            "(SELECT SUM(point_data.value) FROM UNNEST(ARRAY_SLICE(site_energy_expected, 23, 29)) AS point_data) "
            "AS site_energy_expected_last_7_days,"
            "(SELECT SUM(point_data.value) FROM UNNEST(ARRAY_SLICE(site_energy_actual, 0, 29)) AS point_data) "
            "AS site_energy_actual_last_30_days,"
            "(SELECT SUM(point_data.value) FROM UNNEST(ARRAY_SLICE(site_energy_expected, 0, 29)) AS point_data) "
            "AS site_energy_expected_last_30_days "
            f"FROM {self.bq_engine.bq_dataset_name}.site_energy_actual_vs_expected_daily("
            f"'{interval_start}', '{interval_end}', '{timezone}') WHERE site_id IN ({object_ids})"
        )
        bq_site_data = list(self.bq_engine.execute_query(query))
        return bq_site_data

    def _get_site_cumulative_data_today(self, site_ids: list, interval_start: str, interval_end: str, timezone: str):
        object_ids = ", ".join(map(str, site_ids))
        query = (
            "SELECT SUM(site_energy_actual[OFFSET(0)].value) AS company_energy_actual_today,"
            "SUM(site_energy_expected[OFFSET(0)].value) AS company_energy_expected_today "
            f"FROM {self.bq_engine.bq_dataset_name}.site_energy_actual_vs_expected_daily("
            f"'{interval_start}', '{interval_end}', '{timezone}') WHERE site_id IN ({object_ids})"
        )
        bq_site_data = list(self.bq_engine.execute_query(query))
        return bq_site_data

    def get_site_actual_expected_performance(self, site_ids: list | set, timezone: str = "UTC") -> dict:
        """
        Fetch site actual_kw, expected_kw, performance_index from telemetry bigquery.
        Put site data for past 15 minutes period in cache to save time for query execution.

        Returns: dict -> {'site_id1': (actual_kw, expected_kw),
                          'site_id2': (actual_kw, expected_kw), ...}
        """

        interval_start_time, interval_end_time = self._get_current_time_period(timezone)
        cache_sites = "-".join(map(str, sorted(site_ids)))
        sites_cache_name = f"actual-production-site-{cache_sites}-{interval_start_time}-{interval_end_time}"
        cached_site_data = self.get_from_cache(sites_cache_name)
        if cached_site_data:
            return cached_site_data

        bq_site_data = self.execute_bq_function(
            "site_power_actual_vs_expected", "site_id", site_ids, interval_start_time, interval_end_time, timezone
        )

        telemetry_response = {}
        for site in bq_site_data:
            actual_kw = site["site_power_actual"][0]["value"] or 0
            expected_kw = site["site_power_expected"][0]["value"] or 0
            telemetry_response[int(site["site_id"])] = (actual_kw, expected_kw)

        for site_id in site_ids:
            if not telemetry_response.get(site_id):
                telemetry_response[site_id] = (0, 0)
            # set individual site cache to be used on site actual production chart
            # create unique site cache only if method was called for more than 1 site
            if len(site_ids) > 1:
                individual_site_cache_name = (
                    f"actual-production-site-{site_id}-{interval_start_time}-{interval_end_time}"
                )
                self.set_cache(
                    individual_site_cache_name,
                    {site_id: telemetry_response[site_id]},
                    settings.site_dashboard_expiration_seconds,
                )
        # update cache with new interval BigQuery data and expiration time 15 minutes
        self.set_cache(sites_cache_name, telemetry_response, settings.site_dashboard_expiration_seconds)
        return telemetry_response

    def get_site_today_actual_expected_performance(self, site_ids: list | set, timezone: str = "UTC") -> dict:
        """
        Fetch site actual_kw, expected_kw, performance_index from telemetry bigquery for the current day
        (from midnight to last full 15 minutes).

        Returns: dict -> {'site_id1': (actual_kw, expected_kw),
                          'site_id2': (actual_kw, expected_kw), ...}
        """

        _, interval_end_time = self._get_current_time_period(timezone)
        interval_start_time = (
            datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).strftime(self.time_format)
        )
        cache_sites = "-".join(map(str, sorted(site_ids)))
        sites_cache_name = f"actual-production-site-today-{cache_sites}-{interval_start_time}-{interval_end_time}"
        cached_site_data = self.get_from_cache(sites_cache_name)
        if cached_site_data:
            return cached_site_data

        bq_site_data = self._get_site_cumulative_data_today(site_ids, interval_start_time, interval_end_time, timezone)

        telemetry_response = {}
        if bq_site_data:
            telemetry_response = {
                "cumulative_actual_today": bq_site_data[0]["company_energy_actual_today"] or 0,
                "cumulative_expected_today": bq_site_data[0]["company_energy_expected_today"] or 0,
            }

        # update cache with new interval BigQuery data and expiration time 15 minutes
        self.set_cache(sites_cache_name, telemetry_response, settings.site_dashboard_expiration_seconds)
        return telemetry_response

    def get_site_past_performance(self, site_id: int, timezone: str = "-6") -> dict:
        """Retrieve telemetry site past performance data in timezone UTC-6"""
        utc_minus_6 = datetime_timezone(timedelta(hours=int(timezone)))
        interval_end_time = datetime.now(utc_minus_6).replace(hour=0, minute=0, second=0, microsecond=0)
        interval_start_time = interval_end_time - timedelta(days=7)

        site_cache_name = f"past-performance-site-{site_id}-{interval_start_time}-{interval_end_time}"
        cached_site_data = self.get_from_cache(site_cache_name)
        if cached_site_data:
            return cached_site_data

        bq_site_data = self.execute_bq_function(
            "site_energy_actual_vs_expected_daily",
            "site_id",
            [site_id],
            str(interval_start_time),
            str(interval_end_time),
            timezone,
        )
        site_past_performance = {}
        if bq_site_data:
            for index, row in enumerate(bq_site_data[0]["site_energy_actual"]):
                site_actual_kw = row["value"]
                site_expected_kw = bq_site_data[0]["site_energy_expected"][index]["value"]
                site_past_performance[row["ts"]] = calculate_actual_vs_expected(site_actual_kw, site_expected_kw)
        else:
            # Return zero values if not found in BigQuery
            time_format = "%Y-%m-%dT%H:%M:%S"
            while interval_start_time < interval_end_time:
                site_past_performance[interval_start_time.strftime(time_format)] = 0
                interval_start_time += timedelta(days=1)

        # sort by date in descending order
        site_past_performance = dict(sorted(site_past_performance.items(), reverse=True))
        self.set_cache(site_cache_name, site_past_performance, settings.site_7_days_performance_expiration_seconds)
        return site_past_performance

    def get_site_actual_vs_expected_irradiance(self, site_id: int, timezone: str = "UTC") -> list:
        """Retrieve telemetry site past performance data in timezone UTC-6"""
        interval_end_date = datetime.now(pytz.timezone(timezone)).date()
        interval_start_date = interval_end_date - timedelta(days=7)

        site_cache_name = f"past-performance-site-{site_id}-{interval_start_date}-{interval_end_date}"
        cached_site_data = self.get_from_cache(site_cache_name)
        if cached_site_data:
            return cached_site_data

        bq_site_data = self.execute_bq_function(
            "site_power_actual_vs_expected_and_irradiance",
            "site_id",
            [site_id],
            str(interval_start_date),
            str(interval_end_date),
            timezone,
        )
        site_power_actual_vs_expected = []
        if bq_site_data:
            for index, row in enumerate(bq_site_data[0]["site_power_actual"]):
                site_actual_kw = row["value"] or 0
                site_expected_kw = bq_site_data[0]["site_power_expected"][index]["value"] or 0
                site_irradiance = bq_site_data[0]["site_irradiance"][index]["value"] or 0
                site_power_actual_vs_expected.append(
                    {
                        "period": row["ts"],
                        "actual": site_actual_kw,
                        "expected": site_expected_kw,
                        "irradiance": site_irradiance,
                    }
                )
        else:
            # Return zero values if not found in BigQuery
            time_format = "%Y-%m-%dT%H:%M:%S"
            while interval_start_date < interval_end_date:
                period = datetime(interval_start_date.year, interval_start_date.month, interval_start_date.day, 0, 0, 0)
                for hour in range(0, 24):
                    current_period = period + timedelta(hours=hour)
                    site_power_actual_vs_expected.append(
                        {
                            "period": current_period.strftime(time_format),
                            "actual": 0,
                            "expected": 0,
                            "irradiance": 0,
                        }
                    )
                interval_start_date += timedelta(days=1)

        self.set_cache(
            site_cache_name, site_power_actual_vs_expected, settings.site_7_days_performance_expiration_seconds
        )
        return site_power_actual_vs_expected

    def get_site_cumulative_energy(self, site_ids: list | set, timezone: str = "-6") -> dict:
        """Retrieve telemetry site cumulative energy data in timezone UTC-6"""
        utc_minus_6 = datetime_timezone(timedelta(hours=int(timezone)))
        datetime_now = datetime.now(utc_minus_6).replace(hour=0, minute=0, second=0, microsecond=0)
        # daterange should be 1 day ahead to pick up cumulative data for today properly
        interval_end_date = datetime_now + timedelta(days=1)
        interval_start_date = datetime_now - timedelta(days=30)

        cache_sites = "-".join(map(str, sorted(site_ids)))
        site_cache_name = f"cumulative-energy-site-{cache_sites}-{interval_start_date}-{interval_end_date}"
        cached_site_data = self.get_from_cache(site_cache_name)
        if cached_site_data:
            return cached_site_data

        bq_site_data = self._get_site_cumulative_data(
            site_ids,
            str(interval_start_date),
            str(interval_end_date),
            timezone,
        )

        telemetry_response = {}
        for site in bq_site_data:
            cumulative_vs_expected = calculate_actual_vs_expected(
                site.get("site_energy_actual_today", 0), site.get("site_energy_expected_today", 0)
            )
            cumulative_7_days_vs_expected = calculate_actual_vs_expected(
                site.get("site_energy_actual_last_7_days", 0), site.get("site_energy_expected_last_7_days", 0)
            )
            cumulative_30_days_vs_expected = calculate_actual_vs_expected(
                site.get("site_energy_actual_last_30_days", 0), site.get("site_energy_expected_last_30_days", 0)
            )

            telemetry_response[int(site["site_id"])] = (
                cumulative_vs_expected,
                cumulative_7_days_vs_expected,
                cumulative_30_days_vs_expected,
            )

        for site_id in site_ids:
            if not telemetry_response.get(site_id):
                telemetry_response[site_id] = (0, 0, 0)

        # update cache with new interval BigQuery data and expiration time 15 minutes
        self.set_cache(site_cache_name, telemetry_response, settings.site_dashboard_expiration_seconds)
        return telemetry_response
