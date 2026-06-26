from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.crud.company import CompanyCRUD
from app.helpers.solar_position import parse_lon_lat
from app.helpers.telemetry.bigquery import TelemetrySiteBigQuery
from app.helpers.telemetry.legacy_flag import legacy_telemetry_enabled
from app.helpers.telemetry.v2_company_data import (
    aggregate_company_actuals,
    compute_sites_expected_today,
    get_active_baselines,
    get_sites_latest_irradiance,
    get_sites_latest_power,
    get_sites_today_power,
)
from app.models.site import Site
from app.schema.common import calculate_actual_vs_expected
from app.services.telemetry.native_weather_condition_service import (
    derive_site_condition,
)

# Beyond this age, the sites-list weather cell treats the latest irradiance bucket
# as ``stale`` (cosmetic only). The list approximates freshness from the newest
# rollup bucket age rather than running a per-site telemetry-quality probe (which
# would be N+1); the single-site widget uses the precise freshness state.
OBSERVED_CONDITION_LIST_STALE_AFTER = timedelta(hours=6)


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


def extend_company_sites_with_energy_attributes(db_session: Session, sites: list[Site]):
    """Extend each site with its energy attributes for the sites tables.

    Backs the company ``/{company_id}/sites`` and investor ``/sites`` tables. The
    legacy flag selects the data source:

    * flag ON  → the original BigQuery-backed values (unchanged).
    * flag OFF (default) → V2-native PostgreSQL rollups + active baselines
      (:func:`_extend_with_v2_telemetry`). Honest-or-null throughout: a value is
      filled only when the underlying V2 data genuinely supports it, otherwise it
      stays ``None`` (rendered as N/A) — never a fabricated zero.

    The five energy attributes are: ``actual_kw``, ``expected_kw``,
    ``cumulative_vs_expected`` (today %), and ``cumulative_7/30_days_vs_expected``.
    The response shape is identical on both paths.
    """
    if not sites:
        return
    # Native observed-weather indicator (V2 PostgreSQL rollups only). Runs on BOTH
    # the legacy-BigQuery and V2 energy paths so the sites-list weather cell is
    # always the native indicator regardless of the energy source. Read-only and
    # batched; independent of the energy attributes below.
    _extend_with_observed_condition(db_session, sites)
    # V2-native fill (off by default). The decommissioned BigQuery is only used
    # when the legacy flag is explicitly enabled.
    if not legacy_telemetry_enabled():
        _extend_with_v2_telemetry(db_session, sites)
        return
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


def _extend_with_observed_condition(db_session: Session, sites: list[Site]):
    """Set a transient ``observed_condition`` on each site for the weather cell.

    Read-only and BATCHED: one ``get_sites_latest_irradiance`` query for all sites
    (never N+1, never a per-site performance-context build). Calls the same
    :func:`derive_site_condition` single-source-of-truth as the single-site widget
    so the list and the widget agree by construction, but the list is deliberately
    CONSERVATIVE:

    * Freshness is approximated from the newest irradiance bucket age
      (``OBSERVED_CONDITION_LIST_STALE_AFTER``) instead of a precise per-site
      telemetry-quality probe (which would be N+1). No irradiance row ⇒
      ``no_data`` ⇒ an honest ``unavailable`` condition (rendered CloudOff).
    * ``plane_governed=False`` and no temperature are passed — the list never
      claims POA/cell semantics or attaches a temperature it has not governed.
    * Coordinates come from the site's stored ``lon_lat_url`` (no query), so Tier A
      is used where they resolve and Tier B otherwise, matching the widget.

    Never mutates ``site.weather`` (a read-only ORM property); the value is stashed
    on the transient ``site.observed_condition`` attribute that
    ``OMSitesBaseExtendedSchema`` serializes under the ``weather`` alias.
    """
    latest_irr = get_sites_latest_irradiance(db_session, [site.id for site in sites])
    now = datetime.utcnow()
    for site in sites:
        entry = latest_irr.get(site.id)
        if entry is None:
            value, bucket_start, freshness = None, None, "no_data"
        else:
            value, bucket_start = entry
            freshness = "stale" if (now - bucket_start) > OBSERVED_CONDITION_LIST_STALE_AFTER else "fresh"
        site.observed_condition = derive_site_condition(
            latest_irradiance_wm2=value,
            latest_irradiance_at_utc=bucket_start,
            freshness_state=freshness,
            timezone_name=getattr(site, "timezone", None) or "UTC",
            coordinates=parse_lon_lat(getattr(site, "lon_lat_url", None)),
            plane_governed=False,
        )


def _extend_with_v2_telemetry(db_session: Session, sites: list[Site]):
    """Fill the sites-table energy attributes from V2-native PostgreSQL data.

    Read-only. Shares the V2 source-of-truth with the single-site dashboard
    (``apply_v2_actual_production``) and the company aggregation
    (``aggregate_company_actuals``). The instantaneous ``expected_kw`` uses the
    exact same strict latest-actual-bucket alignment as the dashboard's
    ``_expected_power_for_bucket`` (so the table cell matches the drill-down), but
    the cumulative today % is INTENTIONALLY STRICTER than the dashboard: it sums
    expected over only the comparable (``ok`` AND actual-present) buckets, whereas
    the dashboard sums expected over all ``ok`` buckets against actual over all
    power buckets. In gappy data the two can differ; this table has no
    ``expected_state``/coverage caption to explain an approximation, so it reports
    a like-for-like ratio over actual-covered intervals only rather than a looser
    partial-day figure. Field-by-field:

    * ``actual_kw`` — the site's LATEST TODAY power bucket (``None`` when the site
      has no today readings). Today-only — never the most recent bucket of a prior
      day — so it is always aligned to today's ``expected_kw`` and a stale value is
      never compared against today's expected.
    * ``expected_kw`` — expected power at the SAME bucket as the latest ACTUAL
      power bucket, but only when that bucket is ``ok`` (strict, no cross-bucket
      borrowing); else ``None``. Anchoring to the latest actual bucket (not the
      power∪weather union's latest, which can be a later weather-only bucket)
      guarantees that when both ``actual_kw`` and ``expected_kw`` are present they
      refer to the same interval, so the schema-computed ``actual_vs_expected`` is
      an honest like-for-like ratio.
    * ``cumulative_vs_expected`` (today %) — actual-vs-expected of today's energy
      summed over ONLY the comparable buckets (``ok`` AND with an actual power
      reading), so the ratio compares the same intervals on both sides. Computed
      only when at least one comparable bucket exists. A genuine zero (real
      coverage, 0 production) yields ``0``; "no comparable readings" yields
      ``None`` — the two are never conflated.
    * ``cumulative_7/30_days_vs_expected`` — honest ``None``. There is no
      defensible batched V2 multi-day expected, so these stay N/A rather than
      fabricating a value (out of scope: no expected-math changes).

    Uses only batched helpers (one windowed power query + one baseline query + one
    windowed expected query) — no N+1, no BigQuery, no provider/credential calls.
    """
    site_ids = [site.id for site in sites]
    power_by_site = get_sites_today_power(db_session, sites)
    baselines_by_site = get_active_baselines(db_session, site_ids)

    # Compute expected only for sites with real today power AND an active baseline
    # (a baseline-less or readings-less site can only ever be honest N/A here).
    sites_to_compute = [
        site
        for site in sites
        if (power := power_by_site.get(site.id))
        and power.bucket_count > 0
        and site.id in baselines_by_site
    ]
    expected_by_site = compute_sites_expected_today(db_session, sites_to_compute, baselines_by_site)

    for site in sites:
        power = power_by_site.get(site.id)
        has_today_power = bool(power and power.bucket_count > 0)
        expected = expected_by_site.get(site.id)

        site.actual_kw = power.latest_power_kw if has_today_power else None
        # Strict alignment: expected power at the SAME bucket as actual_kw (the
        # latest actual power bucket), only when that bucket is ``ok`` — never the
        # union's latest (possibly later, weather-only) bucket. So when both are
        # present the schema-computed ``actual_vs_expected`` compares like-for-like.
        site.expected_kw = expected.expected_power_at_latest_actual_kw if expected else None
        if expected is not None:
            # Like-for-like today %: actual and expected summed over the SAME
            # comparable buckets (``ok`` AND with an actual power reading). None-safe:
            # None when there is no comparable bucket (no real coverage) or when
            # expected is 0; a genuine zero (real coverage, 0 actual) yields 0.
            site.cumulative_vs_expected = calculate_actual_vs_expected(
                expected.comparable_actual_energy_kwh,
                expected.comparable_expected_energy_kwh,
            )
        else:
            site.cumulative_vs_expected = None
        site.cumulative_7_days_vs_expected = None
        site.cumulative_30_days_vs_expected = None
