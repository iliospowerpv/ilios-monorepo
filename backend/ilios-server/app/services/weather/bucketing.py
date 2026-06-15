"""Epoch-anchored bucketing for native weather observations (W2).

This mirrors the V2 telemetry rollup bucket grid exactly — same widths
(15m/30m/1h/1d) floored from the Unix epoch — so a readiness/replay computation
lands on the SAME bucket boundaries the expected calc already consumes from
``telemetry_site_interval_rollups``. Keeping the grids identical is what lets
historical observations slot into the existing expected pipeline without a
separate replay engine and without shifting any numbers.

Strict W2 semantics (mirroring ``weather_resolver`` and the W0 model invariants):

* Only **POA** irradiance is physics-usable. GHI/DNI/DHI/unknown irradiance is
  stored verbatim but NEVER converted to POA and never counted as usable.
* Only **cell / module / modeled_cell** temperature is physics-usable. Ambient
  and unknown temperature are stored verbatim but NEVER converted to cell and
  never counted as usable.
* Buckets are averaged over the usable rows that fall in them. A bucket with no
  usable row yields ``None`` (never zero-filled, never fabricated).

Everything here is a pure function with no DB and no external/provider/secret/
BigQuery/Firestore access, so it is fully unit-testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

from app.models.weather import WeatherConfidence, WeatherIrradiancePlane, WeatherTemperatureType

# Epoch-anchored bucket widths — must stay in lockstep with
# ``app/services/telemetry/rollup_service.py`` so weather and telemetry share a
# grid.
_EPOCH = datetime(1970, 1, 1)
BUCKET_SIZES: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "30m": timedelta(minutes=30),
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
}

# Physics-usable semantics. These intentionally mirror the resolver's
# ``CELL_USABLE_TEMPERATURE_TYPES`` and the POA-only irradiance rule; they are
# restated here (rather than imported) so this module stays import-cycle-free —
# the resolver imports bucketing, not the other way around.
USABLE_IRRADIANCE_PLANES = frozenset({WeatherIrradiancePlane.poa.value})
USABLE_TEMPERATURE_TYPES = frozenset(
    {
        WeatherTemperatureType.cell.value,
        WeatherTemperatureType.module.value,
        WeatherTemperatureType.modeled_cell.value,
    }
)

# Coarse confidence ordering (unknown is the most conservative / lowest).
CONFIDENCE_RANK = {
    WeatherConfidence.unknown.value: 0,
    WeatherConfidence.low.value: 1,
    WeatherConfidence.medium.value: 2,
    WeatherConfidence.high.value: 3,
}


def _enum_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else value


def floor_to_bucket(ts: datetime, bucket_size: str) -> datetime:
    """Floor ``ts`` to the start of its bucket, measured from the Unix epoch."""
    size = BUCKET_SIZES.get(bucket_size)
    if size is None:
        raise ValueError(f"Unsupported bucket size: {bucket_size!r}")
    bucket_seconds = size.total_seconds()
    elapsed = (ts - _EPOCH).total_seconds()
    floored = (elapsed // bucket_seconds) * bucket_seconds
    return _EPOCH + timedelta(seconds=floored)


def expected_bucket_starts(
    start: datetime, end: datetime, bucket_size: str
) -> list[datetime]:
    """The epoch-anchored bucket-start grid covering ``[start, end]``.

    Begins at the first bucket boundary ``>= start`` (matching the rollup
    ``get_series`` filter ``bucket_start >= start``) and steps by the bucket
    width through ``end`` inclusive. This is the honest *denominator* for
    coverage: the buckets a fully-populated window WOULD contain.
    """
    size = BUCKET_SIZES.get(bucket_size)
    if size is None:
        raise ValueError(f"Unsupported bucket size: {bucket_size!r}")
    if end < start:
        return []
    first = floor_to_bucket(start, bucket_size)
    if first < start:
        first = first + size
    out: list[datetime] = []
    cursor = first
    while cursor <= end:
        out.append(cursor)
        cursor = cursor + size
    return out


def min_confidence(bands: Iterable[Optional[str]]) -> Optional[str]:
    """Return the most conservative (lowest-rank) confidence band present."""
    present = [b for b in bands if b is not None]
    if not present:
        return None
    return min(present, key=lambda b: CONFIDENCE_RANK.get(b, 0))


@dataclass(frozen=True)
class BucketAggregate:
    """Aggregated, physics-usable weather for one bucket.

    ``irradiance_poa_wm2`` / ``cell_temperature_f`` are the average of the
    USABLE rows in the bucket (``None`` if none). The ``had_unusable_*`` flags
    record that rows under the physics metric existed but carried non-usable
    semantics (e.g. GHI irradiance, ambient temperature) so readiness can
    disclose "stored but not usable" without ever promoting those values.
    """

    irradiance_poa_wm2: Optional[float] = None
    cell_temperature_f: Optional[float] = None
    irradiance_modeled: bool = False
    cell_temperature_modeled: bool = False
    irradiance_confidence: Optional[str] = None
    cell_temperature_confidence: Optional[str] = None
    had_unusable_irradiance: bool = False
    had_unusable_cell_temperature: bool = False


@dataclass(frozen=True)
class BucketedObservations:
    """All buckets for a window plus the batches/sources that fed usable rows."""

    buckets: dict[datetime, BucketAggregate] = field(default_factory=dict)
    batch_ids: tuple[int, ...] = ()
    source_ids: tuple[int, ...] = ()


def bucket_observations(
    observations: Iterable[Any],
    *,
    bucket_size: str,
    irradiance_metric: str,
    cell_temperature_metric: str,
) -> BucketedObservations:
    """Bucket + average usable weather observations onto the rollup grid.

    Only rows whose metric is ``irradiance_metric`` with an explicit POA plane,
    or ``cell_temperature_metric`` with a cell/module/modeled_cell type, count as
    usable and are averaged per bucket. Rows under those metrics with any other
    semantics are flagged as "had unusable" (stored, never converted). Rows under
    other metrics are ignored here (they remain stored in the table).
    """
    irr_values: dict[datetime, list[float]] = {}
    temp_values: dict[datetime, list[float]] = {}
    irr_modeled: dict[datetime, bool] = {}
    temp_modeled: dict[datetime, bool] = {}
    irr_conf: dict[datetime, list[str]] = {}
    temp_conf: dict[datetime, list[str]] = {}
    irr_unusable: set[datetime] = set()
    temp_unusable: set[datetime] = set()
    batch_ids: set[int] = set()
    source_ids: set[int] = set()
    all_starts: set[datetime] = set()

    for obs in observations:
        bs = floor_to_bucket(obs.obs_ts, bucket_size)
        all_starts.add(bs)
        metric = obs.metric
        if metric == irradiance_metric:
            plane = _enum_value(obs.irradiance_plane)
            if plane in USABLE_IRRADIANCE_PLANES:
                irr_values.setdefault(bs, []).append(float(obs.value))
                irr_modeled[bs] = irr_modeled.get(bs, False) or bool(obs.is_modeled)
                irr_conf.setdefault(bs, []).append(_enum_value(obs.confidence))
                if obs.batch_id is not None:
                    batch_ids.add(obs.batch_id)
                if obs.weather_source_id is not None:
                    source_ids.add(obs.weather_source_id)
            else:
                irr_unusable.add(bs)
        elif metric == cell_temperature_metric:
            temp = _enum_value(obs.temperature_type)
            if temp in USABLE_TEMPERATURE_TYPES:
                temp_values.setdefault(bs, []).append(float(obs.value))
                temp_modeled[bs] = temp_modeled.get(bs, False) or bool(obs.is_modeled)
                temp_conf.setdefault(bs, []).append(_enum_value(obs.confidence))
                if obs.batch_id is not None:
                    batch_ids.add(obs.batch_id)
                if obs.weather_source_id is not None:
                    source_ids.add(obs.weather_source_id)
            else:
                temp_unusable.add(bs)

    buckets: dict[datetime, BucketAggregate] = {}
    for bs in sorted(all_starts):
        irr_list = irr_values.get(bs)
        temp_list = temp_values.get(bs)
        buckets[bs] = BucketAggregate(
            irradiance_poa_wm2=(sum(irr_list) / len(irr_list)) if irr_list else None,
            cell_temperature_f=(
                sum(temp_list) / len(temp_list) if temp_list else None
            ),
            irradiance_modeled=irr_modeled.get(bs, False),
            cell_temperature_modeled=temp_modeled.get(bs, False),
            irradiance_confidence=min_confidence(irr_conf.get(bs, [])),
            cell_temperature_confidence=min_confidence(temp_conf.get(bs, [])),
            had_unusable_irradiance=bs in irr_unusable,
            had_unusable_cell_temperature=bs in temp_unusable,
        )

    return BucketedObservations(
        buckets=buckets,
        batch_ids=tuple(sorted(batch_ids)),
        source_ids=tuple(sorted(source_ids)),
    )
