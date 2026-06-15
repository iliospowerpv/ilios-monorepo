"""W2 historical weather import — native PostgreSQL backfill into W0 tables.

This service imports historical weather observations (from a file/manual source)
into ``weather_observations`` with an immutable ``weather_observation_batches``
provenance record. It is the ONLY new write path in W2 besides profile lifecycle.

Contract (mirroring telemetry ingestion + the W0 invariants):

* **All-or-nothing.** Every row is validated first; if ANY row is invalid the
  whole import raises :class:`WeatherImportValidationError` and writes NOTHING —
  a batch can never be half-written.
* **Idempotent.** Each row gets a deterministic ``dedupe_key``; re-importing the
  same window inserts nothing (``ON CONFLICT DO NOTHING``).
* **Naive-UTC.** Timestamps are normalized to the existing naive-UTC convention
  (tz-aware inputs are converted to UTC then stripped).
* **Never coerce semantics.** A row's irradiance plane / temperature type are
  stored exactly as tagged. GHI/ambient/unknown rows are stored verbatim and are
  simply NOT physics-usable; nothing is converted to POA/cell.
* **No external/provider/secret/BigQuery/Firestore access.**
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.crud.weather import (
    WeatherObservationBatchCRUD,
    WeatherObservationCRUD,
    WeatherSourceCRUD,
)
from app.models.weather import (
    WeatherConfidence,
    WeatherIrradiancePlane,
    WeatherObservationBatchKind,
    WeatherTemperatureType,
)
from app.schema.weather import (
    HistoricalImportPreviewResponse,
    HistoricalImportRequest,
    HistoricalImportResponse,
    WeatherImportRowError,
)
from app.services.weather.bucketing import (
    USABLE_IRRADIANCE_PLANES,
    USABLE_TEMPERATURE_TYPES,
)

# Allowed enum value sets, validated at the service boundary so raw-dict callers
# (and tests) get the same protection the Pydantic API surface gives.
_VALID_PLANES = {e.value for e in WeatherIrradiancePlane}
_VALID_TEMPS = {e.value for e in WeatherTemperatureType}
_VALID_CONFIDENCES = {e.value for e in WeatherConfidence}


class WeatherImportValidationError(Exception):
    """Raised when one or more import rows are invalid. Carries structured
    per-row errors and guarantees NOTHING was written."""

    def __init__(self, errors: list[WeatherImportRowError], message: Optional[str] = None):
        self.errors = errors
        super().__init__(message or f"{len(errors)} invalid weather import row(s)")


@dataclass(frozen=True)
class NormalizedObservation:
    """A validated, normalized import row (naive-UTC, enum strings)."""

    obs_ts: datetime
    metric: str
    value: float
    unit: Optional[str]
    irradiance_plane: str
    temperature_type: str
    is_modeled: bool
    confidence: str
    source_row_id: Optional[str]

    @property
    def physics_usable(self) -> bool:
        """True iff explicitly tagged POA irradiance or a cell-usable temp."""
        return (
            self.irradiance_plane in USABLE_IRRADIANCE_PLANES
            or self.temperature_type in USABLE_TEMPERATURE_TYPES
        )


def _get(row: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from a dict or an attribute-bearing object (row-agnostic)."""
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def _normalize_timestamp(value: Any) -> datetime:
    """Coerce a timestamp to naive-UTC. Accepts datetime or ISO-8601 string."""
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise ValueError("timestamp must be a datetime or ISO-8601 string")
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _normalize_enum(value: Any, default: str, valid: set[str], field: str) -> str:
    if value is None:
        return default
    raw = value.value if hasattr(value, "value") else value
    if raw not in valid:
        raise ValueError(f"invalid {field}: {raw!r}")
    return raw


def _coerce_row(row: Any, index: int) -> tuple[Optional[NormalizedObservation], list[WeatherImportRowError]]:
    """Validate + normalize a single row. Returns ``(obs_or_None, errors)``."""
    errors: list[WeatherImportRowError] = []

    obs_ts: Optional[datetime] = None
    try:
        obs_ts = _normalize_timestamp(_get(row, "timestamp"))
    except Exception as exc:  # noqa: BLE001 - surfaced as a structured error
        errors.append(
            WeatherImportRowError(
                index=index, field="timestamp", message=str(exc),
                value=_safe(_get(row, "timestamp")),
            )
        )

    metric_raw = _get(row, "metric")
    metric = str(metric_raw).strip() if metric_raw is not None else ""
    if not metric:
        errors.append(
            WeatherImportRowError(
                index=index, field="metric", message="metric is required",
                value=_safe(metric_raw),
            )
        )

    value: Optional[float] = None
    try:
        value = float(_get(row, "value"))
        if not math.isfinite(value):
            raise ValueError("value must be a finite number")
    except (TypeError, ValueError) as exc:
        errors.append(
            WeatherImportRowError(
                index=index, field="value", message=str(exc) or "invalid value",
                value=_safe(_get(row, "value")),
            )
        )

    plane = default_temp = confidence = None
    try:
        plane = _normalize_enum(
            _get(row, "irradiance_plane"),
            WeatherIrradiancePlane.unknown.value, _VALID_PLANES, "irradiance_plane",
        )
    except ValueError as exc:
        errors.append(
            WeatherImportRowError(
                index=index, field="irradiance_plane", message=str(exc),
                value=_safe(_get(row, "irradiance_plane")),
            )
        )
    try:
        default_temp = _normalize_enum(
            _get(row, "temperature_type"),
            WeatherTemperatureType.unknown.value, _VALID_TEMPS, "temperature_type",
        )
    except ValueError as exc:
        errors.append(
            WeatherImportRowError(
                index=index, field="temperature_type", message=str(exc),
                value=_safe(_get(row, "temperature_type")),
            )
        )
    try:
        confidence = _normalize_enum(
            _get(row, "confidence"),
            WeatherConfidence.unknown.value, _VALID_CONFIDENCES, "confidence",
        )
    except ValueError as exc:
        errors.append(
            WeatherImportRowError(
                index=index, field="confidence", message=str(exc),
                value=_safe(_get(row, "confidence")),
            )
        )

    if errors:
        return None, errors

    unit_raw = _get(row, "unit")
    src_row_raw = _get(row, "source_row_id")
    return (
        NormalizedObservation(
            obs_ts=obs_ts,
            metric=metric,
            value=value,
            unit=str(unit_raw) if unit_raw is not None else None,
            irradiance_plane=plane,
            temperature_type=default_temp,
            is_modeled=bool(_get(row, "is_modeled", False)),
            confidence=confidence,
            source_row_id=str(src_row_raw) if src_row_raw is not None else None,
        ),
        [],
    )


def _safe(value: Any) -> Any:
    """Make a value JSON-safe for an error payload (datetimes → isoformat)."""
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def validate_rows(
    rows: list[Any],
) -> tuple[list[NormalizedObservation], list[WeatherImportRowError]]:
    """Validate + normalize all rows, collecting every error (not just the first)."""
    normalized: list[NormalizedObservation] = []
    errors: list[WeatherImportRowError] = []
    for i, row in enumerate(rows):
        obs, row_errors = _coerce_row(row, i)
        if row_errors:
            errors.extend(row_errors)
        elif obs is not None:
            normalized.append(obs)
    return normalized, errors


def _summarize(normalized: list[NormalizedObservation]) -> dict[str, Any]:
    distinct_metrics = sorted({o.metric for o in normalized})
    poa = sum(1 for o in normalized if o.irradiance_plane in USABLE_IRRADIANCE_PLANES)
    cell = sum(1 for o in normalized if o.temperature_type in USABLE_TEMPERATURE_TYPES)
    usable = sum(1 for o in normalized if o.physics_usable)
    modeled = sum(1 for o in normalized if o.is_modeled)
    timestamps = [o.obs_ts for o in normalized]
    return {
        "distinct_metrics": distinct_metrics,
        "poa_irradiance_rows": poa,
        "cell_temperature_rows": cell,
        "physics_usable_rows": usable,
        "stored_not_usable_rows": len(normalized) - usable,
        "modeled_rows": modeled,
        "period_start": min(timestamps) if timestamps else None,
        "period_end": max(timestamps) if timestamps else None,
    }


def preview_import(rows: list[Any]) -> HistoricalImportPreviewResponse:
    """Dry-run validate + summarize rows. Writes NOTHING."""
    normalized, errors = validate_rows(rows)
    summary = _summarize(normalized)
    warnings: list[str] = []
    if summary["stored_not_usable_rows"] > 0:
        warnings.append("stored_not_usable_rows_present")
    if summary["modeled_rows"] > 0:
        warnings.append("modeled_rows_present")
    return HistoricalImportPreviewResponse(
        total_rows=len(rows),
        valid_rows=len(normalized),
        invalid_rows=len(rows) - len(normalized),
        errors=errors,
        distinct_metrics=summary["distinct_metrics"],
        physics_usable_rows=summary["physics_usable_rows"],
        poa_irradiance_rows=summary["poa_irradiance_rows"],
        cell_temperature_rows=summary["cell_temperature_rows"],
        stored_not_usable_rows=summary["stored_not_usable_rows"],
        modeled_rows=summary["modeled_rows"],
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        warnings=warnings,
    )


def build_dedupe_key(
    *,
    site_id: int,
    source_id: int,
    obs: NormalizedObservation,
) -> str:
    """Deterministic idempotency key for an observation row.

    Encodes the identity that makes a reading unique: site, source, metric,
    second-resolution timestamp, and the (un-converted) semantic tags. Two
    imports of the same reading collapse to one row; a row with different
    semantics is intentionally distinct (we never silently overwrite semantics).
    """
    modeled_flag = "1" if obs.is_modeled else "0"
    return (
        f"weather:v1:site={site_id}:source={source_id}:metric={obs.metric}"
        f":ts={obs.obs_ts.isoformat(timespec='seconds')}"
        f":plane={obs.irradiance_plane}:temp={obs.temperature_type}"
        f":modeled={modeled_flag}"
    )


def _resolve_source_id(db: Session, *, site_id: int, request: HistoricalImportRequest) -> int:
    """Resolve the weather source id, creating an inline (site-scoped) source if
    the request supplied one. Raises ValueError if an existing id is unknown."""
    if request.weather_source_id is not None:
        source = WeatherSourceCRUD(db).get_visible_to_site(
            site_id=site_id, source_id=request.weather_source_id
        )
        if source is None:
            raise ValueError(
                f"weather_source_id {request.weather_source_id} not found "
                f"or not accessible from site {site_id}"
            )
        return source.id
    spec = request.source
    created = WeatherSourceCRUD(db).create(
        site_id=site_id,
        company_id=None,
        source_type=spec.source_type,
        display_name=spec.display_name,
        provider_key=spec.provider_key,
        is_modeled=spec.is_modeled,
        default_confidence=spec.default_confidence,
        licensing_note=spec.licensing_note,
    )
    return created.id


def run_historical_import(
    db: Session,
    *,
    site_id: int,
    request: HistoricalImportRequest,
    imported_by: Optional[int] = None,
) -> HistoricalImportResponse:
    """Import historical weather all-or-nothing + idempotently.

    Validation runs BEFORE any write; an invalid row raises
    :class:`WeatherImportValidationError` and nothing is persisted.
    """
    normalized, errors = validate_rows(request.rows)
    if errors:
        raise WeatherImportValidationError(errors)

    source_id = _resolve_source_id(db, site_id=site_id, request=request)
    summary = _summarize(normalized)

    batch_kind = request.batch_kind
    if isinstance(batch_kind, WeatherObservationBatchKind):
        batch_kind = batch_kind
    batch = WeatherObservationBatchCRUD(db).create(
        site_id=site_id,
        weather_source_id=source_id,
        batch_kind=batch_kind,
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        row_count=len(normalized),
        unit_system=request.unit_system,
        timezone_alignment_note=request.timezone_alignment_note,
        source_file_id=request.source_file_id,
        imported_by=imported_by,
    )

    rows_to_insert = [
        {
            "site_id": site_id,
            "batch_id": batch.id,
            "weather_source_id": source_id,
            "metric": o.metric,
            "value": o.value,
            "unit": o.unit,
            "obs_ts": o.obs_ts,
            "irradiance_plane": o.irradiance_plane,
            "temperature_type": o.temperature_type,
            "is_modeled": o.is_modeled,
            "confidence": o.confidence,
            "dedupe_key": build_dedupe_key(site_id=site_id, source_id=source_id, obs=o),
        }
        for o in normalized
    ]
    inserted = WeatherObservationCRUD(db).upsert(rows_to_insert)

    warnings: list[str] = []
    if summary["stored_not_usable_rows"] > 0:
        warnings.append("stored_not_usable_rows_present")
    if summary["modeled_rows"] > 0:
        warnings.append("modeled_rows_present")
    if inserted < len(normalized):
        warnings.append("idempotent_duplicates_skipped")

    return HistoricalImportResponse(
        status="succeeded",
        batch_id=batch.id,
        site_id=site_id,
        weather_source_id=source_id,
        rows_received=len(request.rows),
        rows_valid=len(normalized),
        rows_inserted=inserted,
        rows_duplicate=len(normalized) - inserted,
        distinct_metrics=summary["distinct_metrics"],
        physics_usable_rows=summary["physics_usable_rows"],
        stored_not_usable_rows=summary["stored_not_usable_rows"],
        modeled_rows=summary["modeled_rows"],
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        warnings=warnings,
    )
