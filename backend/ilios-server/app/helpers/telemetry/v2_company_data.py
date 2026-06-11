"""Aggregate V2 telemetry rollups into company / investor / portfolio actuals.

Read-only. Reads ONLY the PostgreSQL rollup table
(:class:`TelemetrySiteIntervalRollup`) — never BigQuery, never a
provider/credential call. This is the Phase-2 counterpart to
``v2_chart_data.apply_v2_actual_production`` (which populates a single site):
here we aggregate the same per-site *actual* values across all the sites of a
company (and, by extension, an investor "portfolio", which the platform models
as a per-company aggregation — there is no formal Portfolio entity yet).

V2 carries *actual* telemetry only (AC power). There is no projected/"expected"
baseline metric, so every company/portfolio aggregate intentionally leaves
``expected``/``loss`` ``None`` and reports ``expected_baseline_available=False``;
the frontend renders "N/A" / "Baseline not available" instead of a misleading
0% / 0 kW. Expected/loss will be rebuilt in a future V2 baseline sprint.

Semantics mirror ``apply_v2_actual_production`` so a company total equals the sum
of its site cards:

* ``actual_kw`` (power) — each site's latest hourly avg-power bucket (today's if
  present, otherwise the most recent bucket of any day). Summed across sites.
* ``cumulative_actual_kw`` (today's energy, kWh) — per site, the sum of today's
  hourly buckets weighted by the bucket duration (``Σ avg_kw × bucket_hours``),
  using the SITE's local calendar day (its stored IANA ``timezone``). Summed
  across sites. Each site uses its OWN day boundary — a single company-wide
  boundary would be wrong for a company spanning multiple timezones.

Sites with no V2 rollups contribute nothing (0), which preserves a clean empty
state for companies that are not yet V2-backed.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.helpers.telemetry.v2_chart_data import (
    CHART_BUCKET_SIZE,
    SITE_POWER_METRIC,
    _site_local_day_start_utc,
)
from app.models.telemetry import TelemetrySiteIntervalRollup

logger = logging.getLogger(__name__)

# Hours represented by one rollup bucket, used to weight avg-kW into kWh energy.
# Falls back to 1.0 (treat as hourly) for an unknown size so a new bucket size
# can never raise.
BUCKET_SIZE_TO_HOURS = {"15m": 0.25, "30m": 0.5, "1h": 1.0, "1d": 24.0}


def _bucket_hours(bucket_size: str) -> float:
    return BUCKET_SIZE_TO_HOURS.get(bucket_size, 1.0)


def get_sites_latest_power(
    db_session: Session, site_ids, *, bucket_size: str = CHART_BUCKET_SIZE
) -> dict[int, float]:
    """Latest AC-power bucket value per site (one query, no N+1).

    Returns ``{site_id: latest_avg_kw}`` for every site that has at least one
    power rollup. Sites without any rollup are simply absent from the mapping
    (callers treat a missing site as 0). The "latest" bucket is the most recent
    of any day, matching ``apply_v2_actual_production`` so the company total
    equals the sum of the per-site cards.
    """
    site_ids = list(site_ids)
    if not site_ids:
        return {}
    # PostgreSQL DISTINCT ON (site_id) keeps the first row per site given the
    # ORDER BY, so ordering bucket_start DESC yields each site's newest bucket.
    rows = (
        db_session.query(TelemetrySiteIntervalRollup)
        .filter(
            TelemetrySiteIntervalRollup.site_id.in_(site_ids),
            TelemetrySiteIntervalRollup.normalized_metric == SITE_POWER_METRIC,
            TelemetrySiteIntervalRollup.bucket_size == bucket_size,
        )
        .distinct(TelemetrySiteIntervalRollup.site_id)
        .order_by(
            TelemetrySiteIntervalRollup.site_id.asc(),
            TelemetrySiteIntervalRollup.bucket_start.desc(),
        )
        .all()
    )
    return {row.site_id: float(row.value) for row in rows}


def get_sites_today_energy(
    db_session: Session, sites, *, bucket_size: str = CHART_BUCKET_SIZE
) -> dict[int, float]:
    """Today's energy (kWh) per site = ``Σ avg_kw × bucket_hours``.

    ``sites`` must be Site ORM objects (each provides ``id`` and the IANA
    ``timezone`` used for its local-day boundary). One windowed query fetches all
    candidate buckets from the earliest site's local-midnight onward; each bucket
    is then attributed to its site only if it falls within that site's own
    local-day window. Returns ``{site_id: energy_kwh}`` for every passed site
    (0.0 when the site has no buckets today).
    """
    sites = list(sites)
    if not sites:
        return {}
    now = datetime.utcnow()
    hours = _bucket_hours(bucket_size)
    day_start_by_site = {site.id: _site_local_day_start_utc(site) for site in sites}
    window_start = min(day_start_by_site.values())

    rows = (
        db_session.query(TelemetrySiteIntervalRollup)
        .filter(
            TelemetrySiteIntervalRollup.site_id.in_(list(day_start_by_site.keys())),
            TelemetrySiteIntervalRollup.normalized_metric == SITE_POWER_METRIC,
            TelemetrySiteIntervalRollup.bucket_size == bucket_size,
            TelemetrySiteIntervalRollup.bucket_start >= window_start,
            TelemetrySiteIntervalRollup.bucket_start <= now,
        )
        .all()
    )

    energy: dict[int, float] = {site.id: 0.0 for site in sites}
    for row in rows:
        site_day_start = day_start_by_site.get(row.site_id)
        if site_day_start is not None and row.bucket_start >= site_day_start:
            energy[row.site_id] += float(row.value) * hours
    return energy


def aggregate_company_actuals(
    db_session: Session, sites, *, bucket_size: str = CHART_BUCKET_SIZE
) -> dict:
    """Aggregate the *actual* production of a company's sites from V2 rollups.

    ``sites`` are the (already access-filtered) Site ORM objects to include.
    Returns the shape the company/investor dashboard sections need. Expected and
    loss are ``None`` and ``expected_baseline_available`` is ``False`` (no V2
    baseline yet). ``sites_with_telemetry`` lets a caller distinguish "no V2 data
    at all" from "V2 data exists but production is 0 right now".
    """
    sites = list(sites)
    site_ids = [site.id for site in sites]
    latest_power = get_sites_latest_power(db_session, site_ids, bucket_size=bucket_size)
    today_energy = get_sites_today_energy(db_session, sites, bucket_size=bucket_size)

    return {
        "total_actual_kw": float(sum(latest_power.values())),
        "cumulative_actual_kw": float(sum(today_energy.values())),
        "total_expected_kw": None,
        "cumulative_expected_kw": None,
        "loss": None,
        "expected_baseline_available": False,
        "sites_with_telemetry": len(latest_power),
        "per_site_actual_kw": latest_power,
    }
