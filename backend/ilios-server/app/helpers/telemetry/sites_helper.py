"""
Utilities that helps serve telemetry data on site level
"""

from concurrent.futures import ThreadPoolExecutor

from app.helpers.telemetry.bigquery import TelemetrySiteBigQuery
from app.schema.internal import ProductionChartData


def get_production_chart_data(sites_ids: list):
    """Retrieves ongoing (for last 15min) and cumulated (for today) production info"""
    telemetry_handler = TelemetrySiteBigQuery()
    with ThreadPoolExecutor(max_workers=2) as executor:
        ongoing_performance_task = executor.submit(telemetry_handler.get_site_actual_expected_performance, sites_ids)
        today_cumulated_performance_task = executor.submit(
            telemetry_handler.get_site_today_actual_expected_performance, sites_ids
        )
    sites_ongoing_performance = ongoing_performance_task.result()
    # since ongoing performance is returned per site, sum up for further usage
    sites_ongoing_performance_actual = sites_ongoing_performance_expected = 0
    for metrics in sites_ongoing_performance.values():
        sites_ongoing_performance_actual += metrics[0]
        sites_ongoing_performance_expected += metrics[1]
    sites_today_cumulative_performance = today_cumulated_performance_task.result()
    return ProductionChartData(
        actual_kw=sites_ongoing_performance_actual,
        expected_kw=sites_ongoing_performance_expected,
        cumulative_actual_kw=sites_today_cumulative_performance["cumulative_actual_today"],
        cumulative_expected_kw=sites_today_cumulative_performance["cumulative_expected_today"],
    )


def get_production_chart_data_per_site(site_id: int):
    return get_production_chart_data([site_id])


def get_production_chart_data_per_company_sites(site_ids: list):
    """Sum metrics retrieved for company sites"""
    return get_production_chart_data(site_ids)
