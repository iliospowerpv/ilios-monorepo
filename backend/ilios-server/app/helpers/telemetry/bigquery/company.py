from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone

from app.helpers.telemetry.bigquery.base import BaseTelemetryBigQuery
from app.settings import settings


class TelemetryCompanyBigQuery(BaseTelemetryBigQuery):
    def __init__(self) -> None:
        super().__init__()

    def _get_company_cumulative_data(self, site_ids: list, interval_start: str, interval_end: str, timezone: str):
        # do not make call if no IDs for the filtering provided
        if not site_ids:
            return
        object_ids = ", ".join(map(str, site_ids))
        query = (
            "SELECT SUM(site_energy_actual[OFFSET(0)].value) AS company_energy_actual_today,"
            "SUM(site_energy_expected[OFFSET(0)].value) AS company_energy_expected_today "
            f"FROM {self.bq_engine.bq_dataset_name}.site_energy_actual_vs_expected_daily("
            f"'{interval_start}', '{interval_end}', '{timezone}') WHERE site_id IN ({object_ids})"
        )
        bq_site_data = list(self.bq_engine.execute_query(query))
        return bq_site_data

    def get_company_dashboard_info(self, company_id: int, site_ids: list, timezone: str = "UTC") -> tuple:
        """Fetch company sites actual_kw, expected_kw, performance_index from telemetry bigquery.
        Put data for past 15 minutes period in cache to save time for query execution."""

        interval_start_time, interval_end_time = self._get_current_time_period(timezone)
        # add unique cache name part for group of sites
        company_sites = "-".join(map(str, site_ids))
        company_cache_name = (
            f"actual-production-company-{company_id}-{company_sites}-{interval_start_time}-{interval_end_time}"
        )
        cached_company_data = self.get_from_cache(company_cache_name)
        if cached_company_data:
            return cached_company_data

        bq_company_sites_data = self.execute_bq_function(
            "site_power_actual_vs_expected", "site_id", site_ids, interval_start_time, interval_end_time, timezone
        )

        total_actual_kw, total_expected_kw = 0, 0
        if bq_company_sites_data:
            for site in bq_company_sites_data:
                total_actual_kw += site["site_power_actual"][0]["value"] or 0
                total_expected_kw += site["site_power_expected"][0]["value"] or 0

        # update cache with new interval BigQuery data and expiration time 15 minutes
        self.set_cache(
            company_cache_name, (total_actual_kw, total_expected_kw), settings.site_dashboard_expiration_seconds
        )
        return total_actual_kw, total_expected_kw

    def get_companies_list_actual_production(self, site_ids: list, timezone: str = "UTC") -> list:
        """Fetch sites actual_kw for the companies list table population.
        Put data for past 15 minutes period in cache to save time for query execution."""

        interval_start_time, interval_end_time = self._get_current_time_period(timezone)
        # add unique cache name part for group of sites,
        # sort sites_ids to be sure cache is unique per same set of sites
        site_ids = sorted(site_ids)
        sites_str = "-".join(map(str, site_ids))
        cache_name = f"actual-production-companies-sites-{sites_str}-interval-{interval_start_time}-{interval_end_time}"
        cached_data = self.get_from_cache(cache_name)
        if cached_data is not None:
            return cached_data

        bq_sites_data = self.execute_bq_function(
            "site_power_actual_vs_expected", "site_id", site_ids, interval_start_time, interval_end_time, timezone
        )

        sites_actual_production_response = []
        if bq_sites_data:
            for site in bq_sites_data:
                sites_actual_production_response.append(
                    {
                        "site_id": site["site_id"],
                        "actual_kw": site["site_power_actual"][0]["value"] or 0,
                        "expected_kw": site["site_power_expected"][0]["value"] or 0,
                    }
                )

        # update cache with new interval BigQuery data and expiration time 15 minutes
        self.set_cache(cache_name, sites_actual_production_response, settings.site_dashboard_expiration_seconds)
        return sites_actual_production_response

    def get_company_loses(self, site_ids: list | set, timezone: str = "-6") -> dict:
        """Retrieve company cumulative info for today in timezone UTC-6 to get actual loses"""
        utc_minus_6 = datetime_timezone(timedelta(hours=int(timezone)))
        # end time is full last hour interval, so replace all except hours
        interval_end_date = datetime.now(utc_minus_6).replace(minute=0, second=0, microsecond=0)
        # the chart displays info for today, so start time is the midnight
        interval_start_date = interval_end_date.replace(hour=0)

        cache_sites = "-".join(map(str, sorted(site_ids)))
        cache_name = f"company-loses-sites-{cache_sites}-{interval_start_date}-{interval_end_date}"
        cached_data = self.get_from_cache(cache_name)
        if cached_data:
            return cached_data

        bq_data = self._get_company_cumulative_data(
            site_ids,
            str(interval_start_date),
            str(interval_end_date),
            timezone,
        )

        actual = expected = loses = 0
        if bq_data:
            actual = bq_data[0].get("company_energy_actual_today", 0) or 0
            expected = bq_data[0].get("company_energy_expected_today", 0) or 0

        # calculate loses only in case if expected is bigger than actual
        if expected > actual:
            loses = expected - actual

        response = {
            "cumulative": actual,
            "expected": expected,
            "loss": loses,
        }

        # update cache with new interval BigQuery data and expiration time 15 minutes
        self.set_cache(cache_name, response, settings.site_dashboard_expiration_seconds)
        return response
