from concurrent.futures import ThreadPoolExecutor

from app.crud.company import CompanyCRUD
from app.helpers.telemetry.bigquery import TelemetryCompanyBigQuery, TelemetrySiteBigQuery
from app.helpers.telemetry.sites_helper import get_production_chart_data_per_company_sites
from app.models.site import Site


# TODO potentially can be reused in other methods
def get_company_site_ids_to_limit(company, current_user):
    """Get sites user has access to depends on the system role:
    - for the system user, it's all sites of the company,
    - for the regular user, it's based on the project access"""
    if current_user.is_system_user:
        return [site.id for site in company.sites]

    return [site.id for site in company.sites if site.id in current_user.get_limited_sites_ids()]


def get_company_actual_production_section_with_telemetry(company, site_ids_to_limit, db_session):
    # retrieve details for actual production section
    company_overview = CompanyCRUD(db_session).get_company_with_sites_overview(company.id, site_ids_to_limit)

    # filter out limited user site ids for telemetry
    if site_ids_to_limit:
        site_ids = [site.id for site in company.sites if site.id in site_ids_to_limit]
    else:
        site_ids = [site.id for site in company.sites]

    telemetry_details = get_production_chart_data_per_company_sites(site_ids)

    actual_production_section = {
        "id": company.id,
        "total_sites": company_overview.total_sites,
        "total_actual_kw": telemetry_details.actual_kw,
        "cumulative_actual_kw": telemetry_details.cumulative_actual_kw,
        "cumulative_expected_kw": telemetry_details.cumulative_expected_kw,
        "total_expected_kw": telemetry_details.expected_kw,
        "total_system_size_ac": company_overview.total_system_size_ac,
        "total_system_size_dc": company_overview.total_system_size_dc,
    }
    return actual_production_section


def get_company_actual_vs_expected_production_section_with_telemetry(company, site_ids_to_limit):
    # filter out limited user sites for telemetry
    if site_ids_to_limit:
        company_sites = {site.id: site for site in company.sites if site.id in site_ids_to_limit}
    else:
        company_sites = {site.id: site for site in company.sites}

    sites_actual_production = TelemetryCompanyBigQuery().get_companies_list_actual_production(list(company_sites.keys()))
    company_sites_with_telemetry = []
    for telemetry_site in sites_actual_production:
        if company_sites.get(telemetry_site["site_id"]):
            site = company_sites.pop(telemetry_site["site_id"])
            site.actual_kw, site.expected_kw = telemetry_site["actual_kw"], telemetry_site["expected_kw"]
            company_sites_with_telemetry.append(site)

    # update sites not found in telemetry with zero values
    for site in company_sites.values():
        site.actual_kw, site.expected_kw = 0, 0
        company_sites_with_telemetry.append(site)
    return company_sites_with_telemetry


def extend_company_sites_with_energy_attributes(sites: list[Site]):
    """Extend site object with energy data fetched from telemetry"""
    if sites:
        user_site_ids = {site.id for site in sites}
        telemetry_bq = TelemetrySiteBigQuery()
        # execute BigQuery calls in threads to speedup almost x2
        with ThreadPoolExecutor(max_workers=2) as executor:
            actual_expected_performance_task = executor.submit(
                telemetry_bq.get_site_actual_expected_performance, user_site_ids
            )
            cumulative_energy_task = executor.submit(telemetry_bq.get_site_cumulative_energy, user_site_ids)
        telemetry_sites_actual_expected = actual_expected_performance_task.result()
        telemetry_sites_cumulative = cumulative_energy_task.result()
        for site in sites:
            site.actual_kw, site.expected_kw = telemetry_sites_actual_expected.get(site.id)
            site.cumulative_vs_expected, site.cumulative_7_days_vs_expected, site.cumulative_30_days_vs_expected = (
                telemetry_sites_cumulative.get(site.id)
            )
