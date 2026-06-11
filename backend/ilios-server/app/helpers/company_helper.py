from concurrent.futures import ThreadPoolExecutor

from app.crud.company import CompanyCRUD
from app.helpers.telemetry.bigquery import TelemetrySiteBigQuery
from app.helpers.telemetry.v2_company_data import aggregate_company_actuals, get_sites_latest_power
from app.models.site import Site


# TODO potentially can be reused in other methods
def get_company_site_ids_to_limit(company, current_user):
    """Get sites user has access to depends on the system role:
    - for the system user, it's all sites of the company,
    - for the regular user, it's based on the project access"""
    if current_user.has_platform_bypass:
        return [site.id for site in company.sites]

    return [site.id for site in company.sites if site.id in current_user.get_limited_sites_ids()]


def _company_sites_within_access(company, site_ids_to_limit):
    """Site ORM objects of a company the caller may see (timezone-bearing).

    An empty/falsy ``site_ids_to_limit`` means "no per-site restriction" (e.g. a
    platform-bypass caller), matching the previous BigQuery helper behavior.
    """
    if site_ids_to_limit:
        return [site for site in company.sites if site.id in site_ids_to_limit]
    return list(company.sites)


def get_company_actual_production_section_with_telemetry(company, site_ids_to_limit, db_session):
    """Company actual-production section, aggregated from V2 PostgreSQL rollups.

    Actual power/energy come from ``telemetry_site_interval_rollups`` (no
    BigQuery). Expected is honest-or-null: it is a real sum only when every
    telemetry-backed site has an active baseline that fully computes today
    (``expected_state == 'available'``); otherwise expected is ``None`` and the
    additive ``expected_state`` / coverage counts explain why the frontend should
    render "N/A" / "Baseline not available".
    """
    # retrieve details for actual production section
    company_overview = CompanyCRUD(db_session).get_company_with_sites_overview(company.id, site_ids_to_limit)

    sites = _company_sites_within_access(company, site_ids_to_limit)
    actuals = aggregate_company_actuals(db_session, sites)

    actual_production_section = {
        "id": company.id,
        "total_sites": company_overview.total_sites,
        "total_actual_kw": actuals["total_actual_kw"],
        "cumulative_actual_kw": actuals["cumulative_actual_kw"],
        "cumulative_expected_kw": actuals["cumulative_expected_kw"],
        "total_expected_kw": actuals["total_expected_kw"],
        "total_system_size_ac": company_overview.total_system_size_ac,
        "total_system_size_dc": company_overview.total_system_size_dc,
        "expected_baseline_available": actuals["expected_baseline_available"],
        "expected_state": actuals["expected_state"],
        "sites_with_telemetry": actuals["sites_with_telemetry"],
        "sites_with_active_baseline": actuals["sites_with_active_baseline"],
        "sites_missing_baseline": actuals["sites_missing_baseline"],
    }
    return actual_production_section


def get_company_actual_vs_expected_production_section_with_telemetry(company, site_ids_to_limit, db_session):
    """Per-site actual production for the company bubble chart, from V2 rollups.

    Each site's ``actual_kw`` is its latest V2 power bucket (0.0 when the site
    has no V2 data); ``expected_kw`` is ``None`` (no V2 baseline). The section is
    flagged ``expected_baseline_available=False`` by the caller.
    """
    company_sites = _company_sites_within_access(company, site_ids_to_limit)
    latest_power = get_sites_latest_power(db_session, [site.id for site in company_sites])
    for site in company_sites:
        site.actual_kw = latest_power.get(site.id, 0.0)
        site.expected_kw = None
    return company_sites


def extend_company_sites_with_energy_attributes(sites: list[Site]):
    """Extend site object with energy data fetched from telemetry.

    NOTE: This still reads BigQuery and is intentionally OUT OF SCOPE for the
    Phase-2 V2 company/portfolio actuals migration (it backs the company
    ``/{company_id}/sites`` table, not the company/investor dashboards). It is
    deferred to a later phase rather than partially migrated here.
    """
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
