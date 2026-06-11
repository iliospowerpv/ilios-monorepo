"""Map V2 telemetry rollups into the legacy O&M chart response shapes.

Read-only. Reads ONLY PostgreSQL — the rollup tables for *actuals* and the
``TelemetryExpectedBaseline`` rows for *expected*. Never BigQuery, never a
provider/credential call. Used to give the O&M charts V2-first precedence: when
a site has any V2 rollups, the charts render from V2 and never fall back to
stale BigQuery.

Expected values come ONLY from an active ``weather_adjusted_model`` baseline run
through :func:`compute_site_expected`. If the site has no active baseline (or the
baseline has no computable inputs for the window), ``expected`` is left ``None``
and the section is flagged accordingly — the actual series is always rendered, we
never fabricate an expected line or collapse a missing expected to 0. The
additive ``expected_state`` metadata lets the frontend distinguish fully
available vs partial vs the specific missing reason (see ``ExpectedState``).
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
from app.services.telemetry.expected_service import (
    BUCKET_SIZE_TO_HOURS,
    BucketStatus,
    ExpectedResult,
    ExpectedState,
    _site_local_date,
    compute_site_expected,
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
    """Hourly actual power + irradiance (+ expected when a baseline exists).

    Returns the full section payload (``data`` + the additive metadata) for the
    ``SiteActualVSExpectedPerformanceListSchema``:

    * No active baseline -> ``data`` is the actual power + irradiance series with
      every point's ``expected`` = ``None`` (kept visible, no expected line);
      ``expected_baseline_available`` False, state ``baseline_not_available``.
    * Active baseline -> ``data`` is built from the calc buckets; each point's
      ``expected`` is the computed expected power (``None`` for a
      missing-inputs/pre-PTO bucket — never fabricated). ``actual``/``irradiance``
      are non-optional in the schema, so a bucket missing that metric is 0.0-filled.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=_ACTUAL_VS_EXPECTED_DAYS)
    baseline = _active_baseline(db_session, site.id)
    if baseline is None:
        return {
            "data": _actual_irradiance_series(db_session, site.id, start, end),
            "expected_baseline_available": False,
            "expected_state": ExpectedState.baseline_not_available.value,
        }
    result = compute_site_expected(
        db_session,
        site=site,
        baseline=baseline,
        start=start,
        end=end,
        bucket_size=CHART_BUCKET_SIZE,
    )
    data = [
        {
            "period": b.bucket_start,
            "actual": b.actual_power_kw if b.actual_power_kw is not None else 0.0,
            "expected": b.expected_power_kw,  # None for missing_inputs / pre_pto
            "irradiance": b.irradiance_wm2 if b.irradiance_wm2 is not None else 0.0,
        }
        for b in result.buckets
    ]
    return {
        "data": data,
        "expected_baseline_available": True,
        "expected_state": derive_expected_state(result).value,
    }


def _actual_irradiance_series(
    db_session: Session, site_id: int, start: datetime, end: datetime
) -> list[dict]:
    """Actual power + irradiance points (expected ``None``) for the no-baseline path.

    Union of the power and irradiance buckets, aligned on ``bucket_start``; a
    metric missing for a given bucket is 0.0-filled so the response always
    satisfies the (non-optional) ``actual``/``irradiance`` schema fields.
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
    all_buckets = sorted(set(power_by_ts) | set(irradiance_by_ts))
    return [
        {
            "period": bucket,
            "actual": power_by_ts.get(bucket, 0.0),
            "expected": None,
            "irradiance": irradiance_by_ts.get(bucket, 0.0),
        }
        for bucket in all_buckets
    ]


def build_past_performance_section(db_session: Session, site) -> dict:
    """Daily actual-vs-expected percent over the last ``_PAST_PERFORMANCE_DAYS``.

    Mirrors the legacy daily past-performance chart but from V2:

    * No active baseline -> empty ``data`` flagged ``baseline_not_available`` (the
      frontend shows a no-baseline message rather than empty bars).
    * Active baseline -> hourly ``ok`` buckets are aggregated to SITE-LOCAL days;
      each day's percent is ``Σ actual_kwh / Σ expected_kwh`` over that day's
      ``ok`` buckets only. A day with no ``ok`` bucket (or zero expected energy)
      maps to ``None`` so the frontend shows an honest gap, never a fabricated 0%.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=_PAST_PERFORMANCE_DAYS)
    baseline = _active_baseline(db_session, site.id)
    if baseline is None:
        return {
            "data": {},
            "expected_baseline_available": False,
            "expected_state": ExpectedState.baseline_not_available.value,
        }
    result = compute_site_expected(
        db_session,
        site=site,
        baseline=baseline,
        start=start,
        end=end,
        bucket_size=CHART_BUCKET_SIZE,
    )
    tz_name = getattr(site, "timezone", None) or "UTC"
    bucket_hours = BUCKET_SIZE_TO_HOURS.get(CHART_BUCKET_SIZE, 1.0)

    actual_kwh_by_day: dict[date, float] = defaultdict(float)
    expected_kwh_by_day: dict[date, float] = defaultdict(float)
    days_seen: set[date] = set()
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
    return {
        "data": data,
        "expected_baseline_available": True,
        "expected_state": derive_expected_state(result).value,
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
