"""Map V2 telemetry rollups into the legacy O&M chart response shapes.

Read-only. Reads ONLY the PostgreSQL rollup tables — never BigQuery, never a
provider/credential call. Used to give the O&M charts V2-first precedence: when
a site has any V2 rollups, the charts render from V2 and never fall back to
stale BigQuery.

V2 currently carries *actual* telemetry only (AC power, irradiance, cell
temperature); there is no projected/"expected" baseline metric and no daily
rollup. So the V2-driven charts populate the actual series and intentionally
leave ``expected`` unset (``None``). That is a known visualization gap, not an
error — performance/expected charts (past-performance, inverters-performance)
have no V2 equivalent and stay on BigQuery.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.crud.telemetry_native import TelemetryDeviceRollupCRUD, TelemetrySiteRollupCRUD

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


def site_has_v2_rollups(db_session: Session, site_id: int) -> bool:
    """True if the site has ANY V2 rollups (the V2-vs-BigQuery precedence switch)."""
    return TelemetrySiteRollupCRUD(db_session).has_rollups(site_id)


def build_actual_vs_expected_series(db_session: Session, site_id: int) -> list[dict]:
    """Hourly actual power + irradiance from V2 for the last N days.

    ``expected`` is intentionally ``None`` (no V2 projection baseline). The
    points are the union of the power and irradiance buckets, aligned on
    ``bucket_start``; a metric missing for a given bucket is filled with 0.0 so
    the response always satisfies the (non-optional) ``actual``/``irradiance``
    schema fields.
    """
    crud = TelemetrySiteRollupCRUD(db_session)
    end = datetime.utcnow()
    start = end - timedelta(days=_ACTUAL_VS_EXPECTED_DAYS)
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


def apply_v2_actual_production(db_session: Session, site) -> None:
    """Populate a Site ORM's actual-production attributes from V2 rollups.

    * ``actual_kw`` — the latest hourly avg-power bucket (today's if present,
      otherwise the most recent bucket of any day).
    * ``cumulative_actual_kw`` — today's energy (kWh) approximated as the sum of
      today's hourly avg-power buckets (avg kW over a 1h bucket ~= kWh).
    * ``expected_kw`` / ``cumulative_expected_kw`` — set to ``None`` (no V2
      baseline). ``expected_baseline_available`` is set False so the frontend
      renders "N/A"/"Baseline not available" instead of a misleading 0% / 0 kW.

    "Today" is defined in UTC (matching how readings/rollups are stored), not the
    site's local day — a known approximation.
    """
    crud = TelemetrySiteRollupCRUD(db_session)
    now = datetime.utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_rows = crud.get_series(
        site_id=site.id,
        normalized_metric=SITE_POWER_METRIC,
        bucket_size=CHART_BUCKET_SIZE,
        start=day_start,
        end=now,
    )

    latest_value = today_rows[-1].value if today_rows else None
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
    # No V2 projection baseline: leave expected null (round_to_scale_2 is
    # None-safe) and flag the section so the frontend shows "N/A" instead of 0.
    site.expected_kw = None
    site.cumulative_expected_kw = None
    site.expected_baseline_available = False


def build_v2_inverter_tiles(db_session: Session, site_inverters: list) -> list[dict]:
    """Inverter tiles from V2 device rollups (latest 1h avg AC power bucket).

    V2 has no per-device projection baseline, so every tile reports a NEUTRAL
    status (``performance="N/A"``, rendered gray) and ``expected="N/A"``. The
    ``actual`` value honestly distinguishes the three states the UI must show:

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
