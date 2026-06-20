"""Aggregate V2 telemetry rollups into company / investor / portfolio actuals.

Read-only. Reads ONLY the PostgreSQL rollup table
(:class:`TelemetrySiteIntervalRollup`) — never BigQuery, never a
provider/credential call. This is the Phase-2 counterpart to
``v2_chart_data.apply_v2_actual_production`` (which populates a single site):
here we aggregate the same per-site *actual* values across all the sites of a
company (and, by extension, an investor "portfolio", which the platform models
as a per-company aggregation — there is no formal Portfolio entity yet).

Expected aggregation is HONEST-OR-NULL. A company-level expected is reported only
when EVERY telemetry-backed site (a site with V2 rollups) has an active
``weather_adjusted_model`` baseline AND that baseline computes a full day with no
missing inputs — i.e. when the company ``expected_state`` is ``available``. In any
other case (some sites lack a baseline, or a site's inputs are missing/pre-PTO)
the aggregate expected is ``None`` so the frontend never shows a misleading
partial-coverage sum; the additive ``expected_state`` (+ the
``sites_with_telemetry`` / ``sites_with_active_baseline`` / ``sites_missing_baseline``
counts) explains exactly why. ``expected_baseline_available`` stays ``True`` only
when a real aggregate is present.

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
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD
from app.helpers.telemetry.v2_chart_data import (
    CHART_BUCKET_SIZE,
    SITE_POWER_METRIC,
    _site_local_day_start_utc,
)
from app.models.telemetry import TelemetrySiteIntervalRollup
from app.services.telemetry.expected_service import (
    CELL_TEMPERATURE_METRIC,
    IRRADIANCE_METRIC,
    BaselineParams,
    BucketInput,
    BucketStatus,
    ExpectedResult,
    ExpectedState,
    OverallStatus,
    compute_expected_buckets,
    derive_expected_state,
)
from app.services.telemetry.baseline_physics_validation import (
    is_active_baseline_blocking,
)

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


@dataclass(frozen=True)
class SiteTodayPower:
    """Per-site today SITE_POWER summary for the sites tables.

    * ``energy_kwh`` — today's energy (``Σ avg_kw × bucket_hours``) over the
      site's local day.
    * ``bucket_count`` — number of today power buckets. This distinguishes a
      genuine zero (``energy_kwh == 0`` with ``bucket_count > 0`` — a real "no
      production right now") from "no readings at all" (``bucket_count == 0``),
      so a missing reading is never turned into a fabricated 0%.
    * ``latest_power_kw`` — avg power at the LATEST today bucket (``None`` when
      there are no today buckets). Using today's latest (not the most recent of
      any day) keeps ``actual_kw`` aligned to today's expected power, never
      comparing a stale prior-day actual against today's expected.
    """

    energy_kwh: float
    bucket_count: int
    latest_power_kw: Optional[float]


def get_sites_today_power(
    db_session: Session, sites, *, bucket_size: str = CHART_BUCKET_SIZE
) -> dict[int, SiteTodayPower]:
    """Per-site today SITE_POWER summary in ONE windowed query (no N+1).

    Mirrors :func:`get_sites_today_energy`'s windowed, per-site-local-day
    attribution, but additionally returns the today bucket count and the
    latest-today power so the sites tables can fill ``actual_kw`` honestly (today
    only, aligned to today's expected) and gate the today percentage on real
    actual coverage. Returns an entry for EVERY passed site.
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
    counts: dict[int, int] = {site.id: 0 for site in sites}
    latest_ts: dict[int, Optional[datetime]] = {site.id: None for site in sites}
    latest_val: dict[int, Optional[float]] = {site.id: None for site in sites}
    for row in rows:
        site_day_start = day_start_by_site.get(row.site_id)
        if site_day_start is None or row.bucket_start < site_day_start:
            continue
        value = float(row.value)
        energy[row.site_id] += value * hours
        counts[row.site_id] += 1
        if latest_ts[row.site_id] is None or row.bucket_start > latest_ts[row.site_id]:
            latest_ts[row.site_id] = row.bucket_start
            latest_val[row.site_id] = value
    return {
        site.id: SiteTodayPower(
            energy_kwh=energy[site.id],
            bucket_count=counts[site.id],
            latest_power_kw=latest_val[site.id],
        )
        for site in sites
    }


@dataclass(frozen=True)
class SiteExpectedToday:
    """Per-site today expected summary fed into the company aggregate.

    * ``state`` — the per-site :class:`ExpectedState` over today's site-local day.
    * ``expected_energy_kwh`` — Σ of the ``ok`` buckets' expected energy (``None``
      when no bucket could be computed). Never zero-filled for missing buckets.
    * ``expected_power_latest_kw`` — expected power at the latest bucket of the
      power∪weather union, but only when that bucket is ``ok`` (strict, no
      cross-bucket borrowing); else ``None``. Consumed by the COMPANY AGGREGATE.

    The following are additive and consumed ONLY by the sites tables
    (:func:`app.helpers.company_helper._extend_with_v2_telemetry`); the company
    aggregate ignores them, so they change no aggregate behavior. They exist
    because the union-latest field above can anchor to a later weather-only bucket
    than the latest ACTUAL power bucket the table shows — comparing those would mix
    intervals. These line everything up to the actual power instead:

    * ``expected_power_at_latest_actual_kw`` — expected power at the SAME bucket as
      the latest ACTUAL power bucket, only when that bucket is ``ok``; else
      ``None``. Mirrors ``v2_chart_data._expected_power_for_bucket`` so the table's
      instantaneous actual-vs-expected compares like-for-like.
    * ``comparable_actual_energy_kwh`` / ``comparable_expected_energy_kwh`` — today
      energy summed over ONLY the buckets that are ``ok`` AND have an actual power
      reading, so a today percentage is a true same-interval ratio (never
      expected-over-more-buckets-than-actual). Both ``None`` when no such bucket
      exists, so a missing reading is never turned into a fabricated 0%.
    """

    state: ExpectedState
    expected_energy_kwh: Optional[float]
    expected_power_latest_kw: Optional[float]
    expected_power_at_latest_actual_kw: Optional[float] = None
    comparable_actual_energy_kwh: Optional[float] = None
    comparable_expected_energy_kwh: Optional[float] = None


def get_active_baselines(db_session: Session, site_ids) -> dict:
    """Batched ``{site_id: active weather_adjusted_model baseline}`` (one query)."""
    return TelemetryExpectedBaselineCRUD(db_session).get_active_for_sites(list(site_ids))


def compute_sites_expected_today(
    db_session: Session, sites, baselines_by_site: dict, *, bucket_size: str = CHART_BUCKET_SIZE
) -> dict:
    """Per-site today expected for every site that has an active baseline.

    Pulls power + irradiance + cell-temperature rollups for ALL the sites in ONE
    windowed query (no N×3 per-site ``get_series``), attributes each bucket to its
    site's OWN local day, then runs the pure ``compute_expected_buckets`` core per
    site. Only sites present in ``baselines_by_site`` are computed; the returned
    mapping always has an entry for each such site (a baseline with no buckets / no
    inputs today yields ``missing_inputs`` and ``None`` energy — never a fabricated
    value). Returns ``{site_id: SiteExpectedToday}``.
    """
    sites = [site for site in sites if site.id in baselines_by_site]
    if not sites:
        return {}
    now = datetime.utcnow()
    hours = _bucket_hours(bucket_size)
    metrics = (SITE_POWER_METRIC, IRRADIANCE_METRIC, CELL_TEMPERATURE_METRIC)
    day_start_by_site = {site.id: _site_local_day_start_utc(site) for site in sites}
    window_start = min(day_start_by_site.values())

    rows = (
        db_session.query(TelemetrySiteIntervalRollup)
        .filter(
            TelemetrySiteIntervalRollup.site_id.in_(list(day_start_by_site.keys())),
            TelemetrySiteIntervalRollup.normalized_metric.in_(metrics),
            TelemetrySiteIntervalRollup.bucket_size == bucket_size,
            TelemetrySiteIntervalRollup.bucket_start >= window_start,
            TelemetrySiteIntervalRollup.bucket_start <= now,
        )
        .all()
    )

    # {site_id: {metric: {bucket_start: value}}}, only buckets inside each site's
    # own local day (a single company-wide boundary would be wrong across tzs).
    by_site: dict = defaultdict(lambda: {m: {} for m in metrics})
    for row in rows:
        site_day_start = day_start_by_site.get(row.site_id)
        if site_day_start is None or row.bucket_start < site_day_start:
            continue
        metric_map = by_site[row.site_id].get(row.normalized_metric)
        if metric_map is not None:
            metric_map[row.bucket_start] = float(row.value)

    out: dict = {}
    for site in sites:
        out[site.id] = _summarize_site_expected(
            site_id=site.id,
            baseline=baselines_by_site[site.id],
            metric_maps=by_site.get(site.id),
            bucket_hours=hours,
            bucket_size=bucket_size,
            window_start=window_start,
            window_end=now,
        )
    return out


def _summarize_site_expected(
    *, site_id, baseline, metric_maps, bucket_hours, bucket_size, window_start, window_end
) -> SiteExpectedToday:
    """Compute one site's today expected summary from its aligned metric maps."""
    missing = SiteExpectedToday(
        state=ExpectedState.missing_inputs,
        expected_energy_kwh=None,
        expected_power_latest_kw=None,
    )
    if is_active_baseline_blocking(baseline):
        # Fail-closed physics: an active but physically INVALID baseline must
        # NEVER drive expected — not even inside the company sum. Suppress like
        # ``missing`` (expected None, never fabricated/zero) but surface the
        # distinct ``baseline_invalid`` reason. Validated ON READ; never mutates.
        return SiteExpectedToday(
            state=ExpectedState.baseline_invalid,
            expected_energy_kwh=None,
            expected_power_latest_kw=None,
        )
    try:
        params = BaselineParams.from_baseline(baseline)
    except ValueError:
        # Active baseline exists but its physics are incomplete: cannot compute,
        # so surface missing_inputs rather than fabricate an expected.
        logger.warning("company_expected_baseline_incomplete site_id=%s", site_id)
        return missing
    if not metric_maps:
        return missing

    power_map = metric_maps[SITE_POWER_METRIC]
    irradiance_map = metric_maps[IRRADIANCE_METRIC]
    cell_temp_map = metric_maps[CELL_TEMPERATURE_METRIC]
    bucket_starts = sorted(set(power_map) | set(irradiance_map) | set(cell_temp_map))
    bucket_inputs = [
        BucketInput(
            bucket_start=bs,
            irradiance_wm2=irradiance_map.get(bs),
            cell_temperature_f=cell_temp_map.get(bs),
            actual_power_kw=power_map.get(bs),
        )
        for bs in bucket_starts
    ]
    buckets = compute_expected_buckets(params, bucket_inputs, bucket_hours)
    ok_buckets = [b for b in buckets if b.status == BucketStatus.ok]
    expected_energy = sum(b.expected_energy_kwh for b in ok_buckets) if ok_buckets else None
    latest = buckets[-1] if buckets else None
    expected_power_latest = (
        latest.expected_power_kw if latest is not None and latest.status == BucketStatus.ok else None
    )

    # --- Sites-table alignment (additive; the company aggregate ignores these) ---
    # Instantaneous: expected power at the SAME bucket as the latest ACTUAL power
    # bucket, only if that bucket is ``ok`` — strict, no cross-bucket borrowing, so
    # it never anchors to a later weather-only bucket. Mirrors
    # ``v2_chart_data._expected_power_for_bucket``.
    latest_actual_bucket_start = max(power_map) if power_map else None
    expected_power_at_latest_actual = None
    if latest_actual_bucket_start is not None:
        for b in buckets:
            if b.bucket_start == latest_actual_bucket_start:
                if b.status == BucketStatus.ok:
                    expected_power_at_latest_actual = b.expected_power_kw
                break
    # Cumulative: sum actual AND expected over ONLY the buckets that are ``ok`` AND
    # have an actual power reading, so the today ratio compares the same intervals
    # (never expected-over-more-buckets-than-actual). ``None`` when no such bucket
    # exists, so a missing reading never becomes a fabricated 0%.
    comparable_buckets = [b for b in ok_buckets if b.actual_power_kw is not None]
    comparable_actual_energy = None
    comparable_expected_energy = None
    if comparable_buckets:
        comparable_actual_energy = sum(
            b.actual_power_kw * bucket_hours for b in comparable_buckets
        )
        comparable_expected_energy = sum(
            b.expected_energy_kwh for b in comparable_buckets
        )

    result = ExpectedResult(
        overall_status=OverallStatus.ok,
        baseline_id=getattr(baseline, "id", None),
        baseline_type=None,
        bucket_size=bucket_size,
        window_start=window_start,
        window_end=window_end,
        buckets=buckets,
        expected_energy_kwh=expected_energy,
        actual_energy_kwh=None,
        ok_bucket_count=len(ok_buckets),
        missing_inputs_bucket_count=sum(
            1 for b in buckets if b.status == BucketStatus.missing_inputs
        ),
        pre_pto_bucket_count=sum(1 for b in buckets if b.status == BucketStatus.pre_pto),
    )
    return SiteExpectedToday(
        state=derive_expected_state(result),
        expected_energy_kwh=expected_energy,
        expected_power_latest_kw=expected_power_latest,
        expected_power_at_latest_actual_kw=expected_power_at_latest_actual,
        comparable_actual_energy_kwh=comparable_actual_energy,
        comparable_expected_energy_kwh=comparable_expected_energy,
    )


def aggregate_company_expected(
    company_sites, telemetry_site_ids, baselines_by_site: dict, expected_by_site: dict
) -> dict:
    """Pure honest roll-up of company expected from precomputed per-site data.

    ``telemetry_site_ids`` is the set of site ids that have V2 rollups (the
    company's "telemetry-backed" sites). The aggregate expected is a real number
    ONLY when every telemetry-backed site is fully computable (``available``);
    otherwise it is ``None`` and ``expected_state`` explains the gap. This never
    fabricates and never converts a missing expected into 0.
    """
    company_site_ids = {site.id for site in company_sites}
    telemetry = company_site_ids & set(telemetry_site_ids)
    sites_with_telemetry = len(telemetry)
    sites_with_active_baseline = len(telemetry & set(baselines_by_site))
    sites_missing_baseline = sites_with_telemetry - sites_with_active_baseline

    states = [
        expected_by_site[sid].state
        if sid in baselines_by_site and sid in expected_by_site
        else ExpectedState.baseline_not_available
        for sid in telemetry
    ]

    if sites_with_telemetry == 0:
        company_state = ExpectedState.baseline_not_available
    elif all(state == ExpectedState.available for state in states):
        company_state = ExpectedState.available
    elif all(state == ExpectedState.baseline_not_available for state in states):
        company_state = ExpectedState.baseline_not_available
    else:
        company_state = ExpectedState.partial

    total_expected_kw = None
    cumulative_expected_kw = None
    if company_state == ExpectedState.available:
        # Every telemetry site fully computed -> a real, comparable aggregate.
        cumulative_expected_kw = float(
            sum(expected_by_site[sid].expected_energy_kwh for sid in telemetry)
        )
        powers = [expected_by_site[sid].expected_power_latest_kw for sid in telemetry]
        if all(power is not None for power in powers):
            total_expected_kw = float(sum(powers))

    return {
        "total_expected_kw": total_expected_kw,
        "cumulative_expected_kw": cumulative_expected_kw,
        "expected_baseline_available": company_state == ExpectedState.available,
        "expected_state": company_state.value,
        "sites_with_telemetry": sites_with_telemetry,
        "sites_with_active_baseline": sites_with_active_baseline,
        "sites_missing_baseline": sites_missing_baseline,
    }


def aggregate_company_actuals(
    db_session: Session, sites, *, bucket_size: str = CHART_BUCKET_SIZE
) -> dict:
    """Aggregate the *actual* and *expected* production of a company's sites (V2).

    ``sites`` are the (already access-filtered) Site ORM objects to include.
    Actuals always come from ``telemetry_site_interval_rollups``. Expected is
    honest-or-null: it is a real sum only when every telemetry-backed site has an
    active baseline that fully computes today (``expected_state == 'available'``);
    otherwise expected/loss are ``None`` and the counts + ``expected_state``
    explain why. ``sites_with_telemetry`` distinguishes "no V2 data at all" from
    "V2 data exists but production is 0 right now".
    """
    sites = list(sites)
    site_ids = [site.id for site in sites]
    latest_power = get_sites_latest_power(db_session, site_ids, bucket_size=bucket_size)
    today_energy = get_sites_today_energy(db_session, sites, bucket_size=bucket_size)

    telemetry_site_ids = set(latest_power)
    baselines_by_site = get_active_baselines(db_session, site_ids)
    sites_to_compute = [
        site for site in sites if site.id in telemetry_site_ids and site.id in baselines_by_site
    ]
    expected_by_site = compute_sites_expected_today(
        db_session, sites_to_compute, baselines_by_site, bucket_size=bucket_size
    )
    expected = aggregate_company_expected(
        sites, telemetry_site_ids, baselines_by_site, expected_by_site
    )

    cumulative_actual_kw = float(sum(today_energy.values()))
    cumulative_expected_kw = expected["cumulative_expected_kw"]
    loss = (
        max(cumulative_expected_kw - cumulative_actual_kw, 0.0)
        if cumulative_expected_kw is not None
        else None
    )

    return {
        "total_actual_kw": float(sum(latest_power.values())),
        "cumulative_actual_kw": cumulative_actual_kw,
        "total_expected_kw": expected["total_expected_kw"],
        "cumulative_expected_kw": cumulative_expected_kw,
        "loss": loss,
        "expected_baseline_available": expected["expected_baseline_available"],
        "expected_state": expected["expected_state"],
        "sites_with_telemetry": expected["sites_with_telemetry"],
        "sites_with_active_baseline": expected["sites_with_active_baseline"],
        "sites_missing_baseline": expected["sites_missing_baseline"],
        "per_site_actual_kw": latest_power,
    }
