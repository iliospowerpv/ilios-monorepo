"""Derived interval rollups for native V2 telemetry.

After raw readings are persisted, this service computes time-bucketed
aggregates so dashboards can read pre-aggregated intervals without rescanning
``telemetry_readings``. It writes two derived tables:

* ``telemetry_site_interval_rollups`` — one row per
  ``(site_id, bucket_start, bucket_size, normalized_metric)``.
* ``telemetry_device_interval_rollups`` — one row per
  ``(device_id, bucket_start, bucket_size, normalized_metric)``.

Guarantees:

* **Idempotent.** Buckets upsert on their unique constraint, so re-running the
  same window recomputes rows in place rather than duplicating.
* **Failure-isolated from raw readings.** Rollups are *derived*. This service
  only ever reads ``telemetry_readings`` and upserts into the rollup tables; it
  never writes or deletes raw readings. Any error rolls back only the rollup
  work (which runs in its own transaction, after the readings commit) and is
  returned as a ``failed`` summary — the source-of-truth readings are
  untouched.

Aggregation policy
------------------
Every metric currently in the catalog (AC power kW, cell temperature °F, POA
irradiance W/m²) is an *instantaneous point measurement*, so the correct
interval aggregate is the mean over the bucket (``agg="avg"``). The site rollup
aggregates **all** readings for a metric at the site (both site-level points and
per-device points), giving a site-wide temporal+spatial mean per metric; the
device rollup aggregates per device. If cumulative metrics (e.g. energy kWh) are
added later, the catalog should grow a per-metric default aggregation rather
than special-casing here.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.telemetry_native import (
    TelemetryDeviceRollupCRUD,
    TelemetrySiteRollupCRUD,
)
from app.models.telemetry import TelemetryReading

logger = logging.getLogger(__name__)

# All catalog metrics are instantaneous, so the bucket aggregate is the mean.
_DEFAULT_AGG = "avg"

# Supported bucket widths. Floors are computed against the Unix epoch so bucket
# boundaries are stable and identical across runs (idempotency).
_BUCKET_SIZES: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}

_EPOCH = datetime(1970, 1, 1)

# Safety cap: a manual single-site refresh should never scan an unbounded set.
_MAX_READINGS_SCAN = 500_000


@dataclass
class RollupSummary:
    """Outcome of a rollup pass. ``status`` is succeeded | skipped | failed."""

    site_id: int
    status: str
    bucket_sizes: list[str] = field(default_factory=list)
    readings_scanned: int = 0
    site_rollups_written: int = 0
    device_rollups_written: int = 0
    metrics: list[str] = field(default_factory=list)
    error: Optional[str] = None


def _floor_to_bucket(ts: datetime, size: timedelta) -> datetime:
    """Floor ``ts`` to the start of its bucket, measured from the Unix epoch."""
    bucket_seconds = size.total_seconds()
    elapsed = (ts - _EPOCH).total_seconds()
    floored = (elapsed // bucket_seconds) * bucket_seconds
    return _EPOCH + timedelta(seconds=floored)


def run_rollups_for_window(
    db: Session,
    *,
    site_id: int,
    company_id: int,
    window_start: datetime,
    window_end: datetime,
    bucket_sizes: tuple[str, ...] = ("1h",),
    sync_job_id: Optional[int] = None,
) -> RollupSummary:
    """Compute + upsert site and device rollups for one site over a window.

    Reads the raw readings persisted for ``site_id`` within
    ``[window_start, window_end]`` and writes interval aggregates for each
    requested ``bucket_sizes`` entry. Returns a :class:`RollupSummary`; never
    raises for data/aggregation problems (rolls back its own work and returns a
    ``failed`` summary) so a rollup failure can never undo committed readings.
    """
    sizes = [s for s in bucket_sizes if s in _BUCKET_SIZES]
    summary = RollupSummary(
        site_id=site_id,
        status="succeeded",
        bucket_sizes=sizes,
    )
    if not sizes:
        summary.status = "skipped"
        summary.error = "No valid bucket sizes requested."
        return summary

    try:
        readings = (
            db.query(
                TelemetryReading.device_id,
                TelemetryReading.normalized_metric,
                TelemetryReading.unit,
                TelemetryReading.metric_ts,
                TelemetryReading.value,
            )
            .filter(
                TelemetryReading.site_id == site_id,
                TelemetryReading.metric_ts >= window_start,
                TelemetryReading.metric_ts <= window_end,
            )
            .limit(_MAX_READINGS_SCAN)
            .all()
        )
        summary.readings_scanned = len(readings)
        if not readings:
            summary.status = "skipped"
            return summary

        # Accumulators keyed by bucket identity. Each holds running sum/count to
        # produce the mean, plus a representative unit.
        # site:   (size, bucket_start, metric) -> [sum, count, unit]
        # device: (size, device_id, bucket_start, metric) -> [sum, count, unit]
        site_acc: dict[tuple, list] = {}
        device_acc: dict[tuple, list] = {}
        metrics_seen: set[str] = set()

        for device_id, metric, unit, metric_ts, value in readings:
            if value is None or metric_ts is None:
                continue
            fvalue = float(value)
            metrics_seen.add(metric)
            for size in sizes:
                bucket_start = _floor_to_bucket(metric_ts, _BUCKET_SIZES[size])

                site_key = (size, bucket_start, metric)
                s = site_acc.get(site_key)
                if s is None:
                    site_acc[site_key] = [fvalue, 1, unit]
                else:
                    s[0] += fvalue
                    s[1] += 1

                if device_id is not None:
                    dev_key = (size, device_id, bucket_start, metric)
                    d = device_acc.get(dev_key)
                    if d is None:
                        device_acc[dev_key] = [fvalue, 1, unit]
                    else:
                        d[0] += fvalue
                        d[1] += 1

        calculated_at = datetime.utcnow()

        site_rows = [
            {
                "site_id": site_id,
                "company_id": company_id,
                "bucket_start": bucket_start,
                "bucket_size": size,
                "normalized_metric": metric,
                "agg": _DEFAULT_AGG,
                "value": total / count if count else 0.0,
                "unit": unit,
                "sample_count": count,
                "completeness": None,
                "calculated_at": calculated_at,
            }
            for (size, bucket_start, metric), (total, count, unit) in site_acc.items()
        ]

        device_rows = [
            {
                "device_id": device_id,
                "site_id": site_id,
                "company_id": company_id,
                "bucket_start": bucket_start,
                "bucket_size": size,
                "normalized_metric": metric,
                "agg": _DEFAULT_AGG,
                "value": total / count if count else 0.0,
                "unit": unit,
                "sample_count": count,
                "completeness": None,
                "calculated_at": calculated_at,
            }
            for (size, device_id, bucket_start, metric), (
                total,
                count,
                unit,
            ) in device_acc.items()
        ]

        site_written = TelemetrySiteRollupCRUD(db).upsert_rollups(site_rows)
        device_written = TelemetryDeviceRollupCRUD(db).upsert_rollups(device_rows)
        db.commit()

        summary.site_rollups_written = site_written
        summary.device_rollups_written = device_written
        summary.metrics = sorted(metrics_seen)
        return summary
    except Exception as exc:  # noqa: BLE001 — derived; must not affect readings
        db.rollback()
        logger.exception(
            "telemetry_rollup_failed site_id=%s sync_job_id=%s", site_id, sync_job_id
        )
        summary.status = "failed"
        summary.error = f"{type(exc).__name__}: {exc}"
        return summary
