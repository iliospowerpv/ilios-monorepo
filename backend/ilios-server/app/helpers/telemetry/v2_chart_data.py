"""Map V2 telemetry rollups into the legacy O&M chart response shapes.

Read-only. Reads ONLY PostgreSQL — the rollup tables for *actuals* and the
``TelemetryExpectedBaseline`` rows for *expected*. Never BigQuery, never a
provider/credential call. Used to give the O&M charts V2-first precedence: when
a site has any V2 rollups, the charts render from V2 and never fall back to
stale BigQuery.

Expected values come ONLY from ``weather_adjusted_model`` baselines. The HISTORICAL
sections (actual-vs-expected + past-performance) use
:func:`compute_site_expected_period_effective`, which stitches together the baseline
that was ACTIVE during each bucket's period (via ``active_from``/``active_to``) so
activating a new baseline never rewrites prior periods; the live "today/now" fields
(:func:`apply_v2_actual_production`) stay on the current-active baseline. If no
baseline covers a bucket's period (or the baseline has no computable inputs for the
window), ``expected`` is left ``None`` and the section is flagged accordingly — the
actual series is always rendered (including across uncovered pre-baseline gaps), we
never fabricate an expected line or collapse a missing expected to 0. The additive
``expected_state``/``baseline_selection_mode``/per-point ``baseline_id`` metadata lets
the frontend distinguish fully available vs partial vs the specific missing reason
(see ``ExpectedState``).
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD
from app.crud.telemetry_native import TelemetryDeviceRollupCRUD, TelemetrySiteRollupCRUD
from app.schema.common import calculate_actual_vs_expected
from app.services.telemetry.baseline_physics_validation import validate_baseline
from app.services.telemetry.expected_service import (
    BUCKET_SIZE_TO_HOURS,
    BucketStatus,
    ExpectedResult,
    ExpectedState,
    OverallStatus,
    _site_local_date,
    compute_site_expected,
    compute_site_expected_period_effective,
    derive_expected_state,
)

logger = logging.getLogger(__name__)

# Normalized metric keys (see TelemetryMetricCatalog) read by the O&M charts.
SITE_POWER_METRIC = "site_power_ac_kw"
IRRADIANCE_METRIC = "irradiance_wm2"
# Per-device AC power, used for the V2 inverter tiles' latest actual value.
DEVICE_POWER_METRIC = "device_power_ac_kw"

# The charts read the hourly rollup, matching the legacy hourly BigQuery series.
CHART_BUCKET_SIZE = "1h"

# Days of hourly history the actual-vs-expected line shows (matches the legacy
# BigQuery 7-day window).
_ACTUAL_VS_EXPECTED_DAYS = 7

# Days of daily past-performance shown (matches the legacy BigQuery 7-day window).
_PAST_PERFORMANCE_DAYS = 7


def site_has_v2_rollups(db_session: Session, site_id: int) -> bool:
    """True if the site has ANY V2 rollups (the V2-vs-BigQuery precedence switch)."""
    return TelemetrySiteRollupCRUD(db_session).has_rollups(site_id)


def _active_baseline(db_session: Session, site_id: int):
    """The active ``weather_adjusted_model`` baseline for a site, or ``None``.

    This is the ONLY thing that may drive a live expected line — drafts,
    design-estimate baselines and approved-but-not-active baselines never do.
    """
    return TelemetryExpectedBaselineCRUD(db_session).get_active(site_id)


def _evaluate_active_baseline(baseline):
    """``(is_blocking, report)`` for an active baseline, validated ON READ.

    Pure / read-only: runs the fail-closed physics validation against the row
    WITHOUT mutating or persisting anything, so a still-active but physically
    invalid baseline (e.g. the legacy Site-4 #3) surfaces as ``baseline_invalid``
    on every read without a migration/backfill. ``report`` is ``None`` when there
    is no active baseline.
    """
    if baseline is None:
        return False, None
    report = validate_baseline(baseline, validation_source_mode="read_time")
    return report.is_blocking, report


def _baseline_invalid_meta(baseline, report) -> dict:
    """Additive response fields for a suppressed-because-invalid active baseline.

    Surfaces WHY the expected curve is suppressed (the validation summary +
    policy version) and the invalid baseline's id so the frontend can deep-link
    to the Draft Baseline Review / replacement flow. Read-only — never mutates.
    The expected curve itself is left ``None`` (never fabricated, never 0).
    """
    return {
        "baseline_invalid": True,
        "invalid_baseline_id": getattr(baseline, "id", None),
        "baseline_validation_summary": report.summary if report else None,
        "baseline_validation_policy_version": (
            report.policy_version if report else None
        ),
        "required_action": "replace_baseline",
    }


def _invalid_segments_payload(result) -> Optional[list[dict]]:
    """Serialize a period-effective result's invalid baseline segments for the API.

    Additive, read-only: each entry names a SUPERSEDED baseline whose physics
    failed read-time validation and the clipped historical sub-window over which
    its expected was suppressed (those buckets carry ``expected`` ``None`` while
    the actual telemetry stays visible). ``None`` when no segment was invalid, so
    the field is omitted on the healthy/active-invalid/no-baseline paths.
    """
    segments = getattr(result, "invalid_baseline_segments", None)
    if not segments:
        return None
    return [
        {
            "baseline_id": s.baseline_id,
            "segment_start": s.segment_start,
            "segment_end": s.segment_end,
            "validation_summary": s.validation_summary,
            "policy_version": s.policy_version,
        }
        for s in segments
    ]


def _bucket_actual_energy_kwh(bucket, bucket_hours: float) -> float:
    """Actual energy (kWh) for one bucket from its avg power, 0.0 when missing."""
    if bucket.actual_power_kw is None:
        return 0.0
    return bucket.actual_power_kw * bucket_hours


def apply_v2_actual_production(db_session: Session, site) -> None:
    """Populate a Site ORM's actual-production attributes from V2.

    Actuals (always rendered):

    * ``actual_kw`` — the latest hourly avg-power bucket (today's if present,
      otherwise the most recent bucket of any day).
    * ``cumulative_actual_kw`` — today's energy (kWh) approximated as the sum of
      today's hourly avg-power buckets (avg kW over a 1h bucket ~= kWh).

    Expected (only from an active baseline; otherwise ``None``):

    * ``expected_kw`` — the expected power for the SAME bucket as ``actual_kw``,
      but only if that bucket is ``ok`` (strict alignment, no cross-bucket
      borrowing). ``None`` when there is no baseline, no matching bucket, or that
      bucket could not be computed (missing inputs / pre-PTO).
    * ``cumulative_expected_kw`` — today's expected energy over the ``ok`` buckets
      (``None`` when nothing computed). NOTE: when ``expected_state`` is
      ``partial`` this is summed over fewer buckets than ``cumulative_actual_kw``,
      so the derived percent is approximate — the frontend uses ``expected_state``
      to caption that.

    ``expected_baseline_available`` / ``expected_state`` / ``baseline_id`` are set
    so the frontend can render "N/A"/"Baseline not available" instead of a
    misleading 0% / 0 kW.

    "Today" is the SITE's local day (its stored IANA ``timezone``), converted to
    UTC for the rollup query since readings/rollups are stored naive-UTC. Falls
    back to UTC when the site has no/invalid timezone.
    """
    crud = TelemetrySiteRollupCRUD(db_session)
    now = datetime.utcnow()
    day_start = _site_local_day_start_utc(site)
    today_rows = crud.get_series(
        site_id=site.id,
        normalized_metric=SITE_POWER_METRIC,
        bucket_size=CHART_BUCKET_SIZE,
        start=day_start,
        end=now,
    )

    latest_today = today_rows[-1] if today_rows else None
    latest_value = latest_today.value if latest_today is not None else None
    if latest_value is None:
        # No buckets today — fall back to the most recent power bucket overall.
        for row in crud.get_latest_per_metric(site.id, bucket_size=CHART_BUCKET_SIZE):
            if row.normalized_metric == SITE_POWER_METRIC:
                latest_value = row.value
                break

    site.actual_kw = float(latest_value) if latest_value is not None else 0.0
    site.cumulative_actual_kw = (
        float(sum(row.value for row in today_rows)) if today_rows else 0.0
    )

    baseline = _active_baseline(db_session, site.id)
    if baseline is None:
        # No active baseline: keep actuals visible, leave expected null (the
        # round_to_scale_2 validator is None-safe) and flag no-baseline.
        site.expected_kw = None
        site.cumulative_expected_kw = None
        site.expected_baseline_available = False
        site.expected_state = ExpectedState.baseline_not_available.value
        site.baseline_id = None
        return

    is_blocking, report = _evaluate_active_baseline(baseline)
    if is_blocking:
        # Active baseline EXISTS but is physically invalid (validated ON READ,
        # no mutation): suppress the expected comparison (None, never 0) while
        # keeping actuals visible, and surface why + the invalid baseline id so
        # the frontend can deep-link to the replacement flow.
        site.expected_kw = None
        site.cumulative_expected_kw = None
        site.expected_baseline_available = False
        site.expected_state = ExpectedState.baseline_invalid.value
        site.baseline_id = baseline.id
        meta = _baseline_invalid_meta(baseline, report)
        site.baseline_invalid = meta["baseline_invalid"]
        site.invalid_baseline_id = meta["invalid_baseline_id"]
        site.baseline_validation_summary = meta["baseline_validation_summary"]
        site.baseline_validation_policy_version = meta[
            "baseline_validation_policy_version"
        ]
        site.required_action = meta["required_action"]
        return

    result = compute_site_expected(
        db_session,
        site=site,
        baseline=baseline,
        start=day_start,
        end=now,
        bucket_size=CHART_BUCKET_SIZE,
    )
    site.expected_baseline_available = True
    site.expected_state = derive_expected_state(result).value
    site.baseline_id = result.baseline_id
    # Today's expected energy over ok buckets (None when nothing computed).
    site.cumulative_expected_kw = result.expected_energy_kwh
    # Instantaneous expected aligned to the SAME bucket as actual_kw, only if ok.
    site.expected_kw = _expected_power_for_bucket(result, latest_today)


def _expected_power_for_bucket(
    result: ExpectedResult, actual_bucket
) -> Optional[float]:
    """Expected power for the bucket matching ``actual_bucket``'s start, if ``ok``.

    Strict alignment: returns ``None`` unless the calc produced an ``ok`` bucket
    at exactly the actual bucket's ``bucket_start`` — never borrows a neighbouring
    bucket's expected, so the instantaneous percent compares like-for-like.
    """
    if actual_bucket is None:
        return None
    for b in result.buckets:
        if b.bucket_start == actual_bucket.bucket_start:
            if b.status == BucketStatus.ok:
                return b.expected_power_kw
            return None
    return None


def build_actual_vs_expected_section(db_session: Session, site) -> dict:
    """Hourly actual power + irradiance (+ period-effective expected).

    Returns the full section payload (``data`` + the additive metadata) for the
    ``SiteActualVSExpectedPerformanceListSchema``. Expected is selected
    PERIOD-EFFECTIVELY: each historical bucket uses the baseline that was active
    during that bucket's period (see
    :func:`compute_site_expected_period_effective`), so activating a new baseline
    never silently rewrites the prior expected line.

    * No baseline overlaps the window -> ``data`` is the actual power + irradiance
      series with every point's ``expected`` = ``None`` (kept visible, no expected
      line); ``expected_baseline_available`` False, state ``baseline_not_available``.
    * Baseline(s) overlap -> ``data`` is the stitched calc buckets (each point's
      ``expected`` is the computed expected power, ``None`` for a
      missing-inputs/pre-PTO bucket — never fabricated) PLUS the GAP regions:
      timestamps that have actual/irradiance data but fall in a period NO baseline
      covered, rendered with ``expected``/``baseline_id`` = ``None`` so the actual
      line stays continuous and honest. ``actual``/``irradiance`` are non-optional
      in the schema, so a bucket missing that metric is 0.0-filled. Each point
      carries the ``baseline_id`` that produced its expected.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=_ACTUAL_VS_EXPECTED_DAYS)
    active = _active_baseline(db_session, site.id)
    is_blocking, report = _evaluate_active_baseline(active)
    if is_blocking:
        # Active baseline is physically INVALID: render actuals only (expected
        # null per point, never fabricated/0) and flag ``baseline_invalid`` so the
        # frontend shows the replacement banner. Mirrors the no-baseline branch;
        # validated ON READ, the row is never mutated.
        return {
            "data": _actual_irradiance_series(db_session, site.id, start, end),
            "expected_baseline_available": False,
            "expected_state": ExpectedState.baseline_invalid.value,
            "baseline_selection_mode": None,
            **_baseline_invalid_meta(active, report),
        }
    result = compute_site_expected_period_effective(
        db_session,
        site=site,
        start=start,
        end=end,
        bucket_size=CHART_BUCKET_SIZE,
    )
    if result.overall_status == OverallStatus.baseline_not_available:
        return {
            "data": _actual_irradiance_series(db_session, site.id, start, end),
            "expected_baseline_available": False,
            "expected_state": ExpectedState.baseline_not_available.value,
            "baseline_selection_mode": result.baseline_selection_mode,
        }
    data = [
        {
            "period": b.bucket_start,
            "actual": b.actual_power_kw if b.actual_power_kw is not None else 0.0,
            "expected": b.expected_power_kw,  # None for missing_inputs / pre_pto
            "irradiance": b.irradiance_wm2 if b.irradiance_wm2 is not None else 0.0,
            "baseline_id": b.baseline_id,
        }
        for b in result.buckets
    ]
    # Gap regions: timestamps with actual/irradiance data in a period no baseline
    # covered. Render them so the actual line stays continuous, but with
    # ``expected``/``baseline_id`` = ``None`` (never a fabricated expected).
    covered_ts = {b.bucket_start for b in result.buckets}
    power_by_ts, irradiance_by_ts = _power_irradiance_maps(
        db_session, site.id, start, end
    )
    gap_ts = (set(power_by_ts) | set(irradiance_by_ts)) - covered_ts
    gap_with_actual = any(ts in power_by_ts for ts in gap_ts)
    for ts in gap_ts:
        data.append(
            {
                "period": ts,
                "actual": power_by_ts.get(ts, 0.0),
                "expected": None,
                "irradiance": irradiance_by_ts.get(ts, 0.0),
                "baseline_id": None,
            }
        )
    data.sort(key=lambda p: p["period"])

    state = derive_expected_state(result)
    if gap_with_actual and state == ExpectedState.available:
        # Real production exists in a period with no covering baseline: the
        # expected line cannot be complete, so the section is partial, not full.
        state = ExpectedState.partial
    return {
        "data": data,
        "expected_baseline_available": True,
        "expected_state": state.value,
        "baseline_selection_mode": result.baseline_selection_mode,
        # Additive: per-segment fail-closed metadata. Non-null only when a
        # superseded baseline was invalid for part of the window (its expected was
        # suppressed → ``state`` is ``partial``/``baseline_invalid``); the actual
        # line for those periods stays visible.
        "invalid_baseline_segments": _invalid_segments_payload(result),
    }


def _power_irradiance_maps(
    db_session: Session, site_id: int, start: datetime, end: datetime
) -> tuple[dict[datetime, float], dict[datetime, float]]:
    """``(power_by_ts, irradiance_by_ts)`` site rollup maps over ``[start, end]``.

    Shared by the no-baseline actual-only series and the period-effective gap-fill
    so both read the SAME power/irradiance window.
    """
    crud = TelemetrySiteRollupCRUD(db_session)
    power_rows = crud.get_series(
        site_id=site_id,
        normalized_metric=SITE_POWER_METRIC,
        bucket_size=CHART_BUCKET_SIZE,
        start=start,
        end=end,
    )
    irradiance_rows = crud.get_series(
        site_id=site_id,
        normalized_metric=IRRADIANCE_METRIC,
        bucket_size=CHART_BUCKET_SIZE,
        start=start,
        end=end,
    )
    power_by_ts = {row.bucket_start: float(row.value) for row in power_rows}
    irradiance_by_ts = {row.bucket_start: float(row.value) for row in irradiance_rows}
    return power_by_ts, irradiance_by_ts


def _actual_irradiance_series(
    db_session: Session, site_id: int, start: datetime, end: datetime
) -> list[dict]:
    """Actual power + irradiance points (expected ``None``) for the no-baseline path.

    Union of the power and irradiance buckets, aligned on ``bucket_start``; a
    metric missing for a given bucket is 0.0-filled so the response always
    satisfies the (non-optional) ``actual``/``irradiance`` schema fields.
    """
    power_by_ts, irradiance_by_ts = _power_irradiance_maps(
        db_session, site_id, start, end
    )
    all_buckets = sorted(set(power_by_ts) | set(irradiance_by_ts))
    return [
        {
            "period": bucket,
            "actual": power_by_ts.get(bucket, 0.0),
            "expected": None,
            "irradiance": irradiance_by_ts.get(bucket, 0.0),
            "baseline_id": None,
        }
        for bucket in all_buckets
    ]


def build_past_performance_section(db_session: Session, site) -> dict:
    """Daily actual-vs-expected percent over the last ``_PAST_PERFORMANCE_DAYS``.

    Mirrors the legacy daily past-performance chart but from V2:

    * No baseline overlaps the window -> empty ``data`` flagged
      ``baseline_not_available`` (the frontend shows a no-baseline message).
    * Baseline(s) overlap -> expected is selected PERIOD-EFFECTIVELY (each bucket
      uses the baseline active during its period), then hourly ``ok`` buckets are
      aggregated to SITE-LOCAL days; each day's percent is
      ``Σ actual_kwh / Σ expected_kwh`` over that day's ``ok`` buckets only. A day
      with no ``ok`` bucket (or zero expected energy) maps to ``None`` so the
      frontend shows an honest gap, never a fabricated 0%. ``days_seen`` is seeded
      from the FULL power∪irradiance window so a day that falls in a period with no
      covering baseline still appears (with an honest ``None`` percent), rather than
      silently vanishing from the chart.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=_PAST_PERFORMANCE_DAYS)
    active = _active_baseline(db_session, site.id)
    is_blocking, report = _evaluate_active_baseline(active)
    if is_blocking:
        # Active baseline is physically INVALID: empty daily series flagged
        # ``baseline_invalid`` (the frontend shows the replacement banner instead
        # of a fabricated 0%). Mirrors the no-baseline branch; validated ON READ.
        return {
            "data": {},
            "expected_baseline_available": False,
            "expected_state": ExpectedState.baseline_invalid.value,
            "baseline_selection_mode": None,
            **_baseline_invalid_meta(active, report),
        }
    result = compute_site_expected_period_effective(
        db_session,
        site=site,
        start=start,
        end=end,
        bucket_size=CHART_BUCKET_SIZE,
    )
    if result.overall_status == OverallStatus.baseline_not_available:
        return {
            "data": {},
            "expected_baseline_available": False,
            "expected_state": ExpectedState.baseline_not_available.value,
            "baseline_selection_mode": result.baseline_selection_mode,
        }
    tz_name = getattr(site, "timezone", None) or "UTC"
    bucket_hours = BUCKET_SIZE_TO_HOURS.get(CHART_BUCKET_SIZE, 1.0)

    actual_kwh_by_day: dict[date, float] = defaultdict(float)
    expected_kwh_by_day: dict[date, float] = defaultdict(float)
    days_seen: set[date] = set()
    # Seed days from the FULL power∪irradiance window so days in uncovered periods
    # still show (as honest ``None``); also detect production in a gap period.
    covered_ts = {b.bucket_start for b in result.buckets}
    power_by_ts, irradiance_by_ts = _power_irradiance_maps(
        db_session, site.id, start, end
    )
    gap_with_actual = False
    for ts in set(power_by_ts) | set(irradiance_by_ts):
        days_seen.add(_site_local_date(ts, tz_name))
        if ts not in covered_ts and ts in power_by_ts:
            gap_with_actual = True

    for b in result.buckets:
        local_day = _site_local_date(b.bucket_start, tz_name)
        days_seen.add(local_day)
        # Only ``ok`` buckets contribute to the daily ratio so actual and
        # expected are summed over the SAME comparable buckets.
        if b.status == BucketStatus.ok and b.expected_energy_kwh is not None:
            expected_kwh_by_day[local_day] += b.expected_energy_kwh
            actual_kwh_by_day[local_day] += _bucket_actual_energy_kwh(b, bucket_hours)

    data: dict[datetime, Optional[int]] = {}
    for day in sorted(days_seen):
        day_key = datetime(day.year, day.month, day.day)
        expected_kwh = expected_kwh_by_day.get(day)
        if not expected_kwh:
            # No ok bucket (or genuinely zero expected) that day: honest gap, not 0%.
            data[day_key] = None
        else:
            data[day_key] = calculate_actual_vs_expected(
                actual_kwh_by_day.get(day, 0.0), expected_kwh
            )

    state = derive_expected_state(result)
    if gap_with_actual and state == ExpectedState.available:
        # Real production exists in a period with no covering baseline: incomplete.
        state = ExpectedState.partial
    return {
        "data": data,
        "expected_baseline_available": True,
        "expected_state": state.value,
        "baseline_selection_mode": result.baseline_selection_mode,
        # Additive: per-segment fail-closed metadata. Non-null only when a
        # superseded baseline was invalid for part of the window (those days are
        # excluded from the ratio → an honest ``None`` percent); the days a valid
        # baseline covered keep their percent.
        "invalid_baseline_segments": _invalid_segments_payload(result),
    }


def _site_local_day_start_utc(site) -> datetime:
    """Naive-UTC instant of the site's most recent local midnight.

    Telemetry readings/rollups are stored naive-UTC, so "today" is computed
    against the site's local calendar day (its stored IANA ``timezone``) and the
    day's start is expressed as a naive-UTC datetime for the rollup query. Falls
    back to UTC (with a warning) when the site has no timezone or an unknown one,
    so a bad value can never break the dashboard.
    """
    tz_name = getattr(site, "timezone", None) or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        logger.warning(
            "v2_today_invalid_site_timezone site_id=%s tz=%r falling_back=UTC",
            getattr(site, "id", None),
            tz_name,
        )
        tz = timezone.utc
    local_midnight = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def build_v2_inverter_tiles(db_session: Session, site_inverters: list) -> list[dict]:
    """Inverter tiles from V2 device rollups (latest 1h avg AC power bucket).

    V2 has no per-device projection baseline, and we deliberately do NOT infer a
    device-level expected from the site baseline (the site expected is a whole-
    plant model, not a per-inverter one). So every tile reports a NEUTRAL status
    (``performance="N/A"``, rendered gray) and ``expected="N/A"``. The ``actual``
    value honestly distinguishes the three states the UI must show:

    * mapped inverter WITH V2 data -> ``actual`` = latest bucket value (a real
      float, including a legitimate ``0.0`` e.g. at night);
    * mapped inverter WITHOUT V2 data -> ``actual="N/A"`` (no telemetry yet);
    * unmapped inverter (no telemetry mapping) -> ``actual="N/A"``, as before.

    "Mapped" is keyed on ``telemetry_mapping`` (not ``das_connection_active``) so
    this matches the V2 not-responding logic and stays correct for V2 sites whose
    legacy DAS connection status is not "connected" yet still have native rollups.
    """
    if not site_inverters:
        return []
    site_id = site_inverters[0].site_id
    latest_by_device = {
        row.device_id: float(row.value)
        for row in TelemetryDeviceRollupCRUD(db_session).get_latest_per_device(
            site_id,
            normalized_metric=DEVICE_POWER_METRIC,
            bucket_size=CHART_BUCKET_SIZE,
        )
    }
    tiles: list[dict] = []
    for device in site_inverters:
        tile = {"name": device.name, "performance": "N/A", "expected": "N/A", "actual": "N/A"}
        # Only surface a value for a telemetry-mapped device that actually has
        # V2 data; a real 0.0 reading is kept distinct from "no data" (N/A).
        if device.telemetry_mapping is not None and device.id in latest_by_device:
            tile["actual"] = latest_by_device[device.id]
        tiles.append(tile)
    return tiles
