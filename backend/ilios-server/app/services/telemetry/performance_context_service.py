"""Read-only V2 performance-context aggregator (composition-only).

This service COMPOSES already-computed V2 reads into one canonical envelope:

* the period-effective expected calc (``compute_site_expected_period_effective``),
  used VERBATIM — no physics formula, baseline selection, or pre-PTO/missing
  logic is re-derived here;
* native PostgreSQL rollup actuals (site power / irradiance / cell temperature);
* the governed weather-semantics reconciliation
  (``build_site_semantics_reconciliation``), embedded and projected VERBATIM —
  no label is invented and no state is recomputed;
* the read-only eligibility diagnostics
  (``compute_site_eligibility_diagnostics``), used VERBATIM for the mapping/
  eligibility counts;
* native freshness (latest reading / latest rollup bucket).

It performs ZERO writes/commits and never converts weather semantics. The
0-vs-null integrity rule is enforced throughout: ``null`` means "unavailable"
and ``0`` means "a genuine measured zero" (a negative tare is preserved), and an
expected value or variance is NEVER fabricated when an input is missing.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.crud.telemetry_native import TelemetryReadingCRUD, TelemetrySiteRollupCRUD
from app.helpers.telemetry.v2_chart_data import (
    _active_baseline,
    _baseline_invalid_meta,
    _evaluate_active_baseline,
)
from app.schema.common import calculate_actual_vs_expected
from app.schema.telemetry_v2 import (
    PerformanceContextBaselineStatus,
    PerformanceContextPoint,
    PerformanceContextProvenance,
    PerformanceContextResponse,
    PerformanceContextSummary,
    PerformanceContextTelemetryQuality,
    PerformanceContextWeatherMetric,
    PerformanceContextWeatherSemantics,
    PerformanceContextWindow,
)
from app.services.telemetry.device_eligibility_diagnostics_service import (
    compute_site_eligibility_diagnostics,
)
from app.helpers.solar_position import parse_lon_lat
from app.services.telemetry.native_weather_condition_service import (
    derive_site_condition,
)
from app.schema.telemetry import TelemetryHealthStatus
from app.services.telemetry.expected_service import (
    BUCKET_SIZE_TO_HOURS,
    CELL_TEMPERATURE_METRIC,
    IRRADIANCE_METRIC,
    SITE_POWER_METRIC,
    BucketStatus,
    ExpectedState,
    compute_site_expected_period_effective,
    derive_expected_state,
)
from app.services.telemetry.health_service import compute_site_telemetry_health
from app.services.weather.bucketing import expected_bucket_starts
from app.services.weather.semantics_reconciliation_service import (
    build_site_semantics_reconciliation,
)

logger = logging.getLogger(__name__)

# Map the shared telemetry-health verdict (the SAME computation the
# ``/sites/{id}/health`` endpoint returns) onto the compact 3-state freshness the
# contract exposes. This is a verbatim PROJECTION of the health status — this
# service never re-derives freshness with its own threshold.
_HEALTH_STATUS_TO_FRESHNESS = {
    TelemetryHealthStatus.healthy: "fresh",
    TelemetryHealthStatus.warn: "fresh",
    TelemetryHealthStatus.error: "stale",
    TelemetryHealthStatus.no_data: "no_data",
    TelemetryHealthStatus.not_configured: "no_data",
}

# --- actual_state taxonomy (data-display integrity, §3 of the data contract) -
ACTUAL_AVAILABLE = "available"
ACTUAL_PARTIAL = "partial"
ACTUAL_TELEMETRY_UNAVAILABLE = "telemetry_unavailable"
ACTUAL_TELEMETRY_STALE = "telemetry_stale"
ACTUAL_NO_PRODUCTION = "no_production_during_interval"
ACTUAL_PRE_PTO = "pre_pto"

# Per-bucket expected status -> user-facing expected_state (verbatim mapping).
_STATUS_TO_EXPECTED_STATE = {
    BucketStatus.ok: ExpectedState.available.value,
    BucketStatus.missing_inputs: ExpectedState.missing_inputs.value,
    BucketStatus.pre_pto: ExpectedState.pre_pto.value,
    BucketStatus.baseline_invalid: ExpectedState.baseline_invalid.value,
}

# Most-severe-first ordering for picking the headline weather row (Layer-1 only
# ever emits lowers_confidence / informational, but the ladder is future-proof).
_BLOCKING_ORDER = {
    "blocks_calculation": 0,
    "lowers_confidence": 1,
    "informational": 2,
}


def _enum_value(value: Any) -> Any:
    """Return ``value.value`` for enum-likes, else the value unchanged."""
    return getattr(value, "value", value)


def _to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Coerce a tz-aware instant to naive-UTC; pass naive through unchanged.

    Readings/rollups are stored naive-UTC, so all comparisons use that convention.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _site_local_dt(ts_utc: datetime, tz_name: str) -> Optional[datetime]:
    """Naive-UTC bucket start -> naive site-local datetime (display only)."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 - unknown/invalid IANA name
        logger.warning(
            "performance_context_invalid_timezone tz=%r falling_back=UTC", tz_name
        )
        return ts_utc
    return ts_utc.replace(tzinfo=timezone.utc).astimezone(tz).replace(tzinfo=None)


def _convert_temp(value_f: Optional[float], temp_unit: str) -> Optional[float]:
    """Convert a °F cell temperature to the requested unit (display only).

    Returns ``None`` unchanged (never fabricates a 0). ``temp_unit`` is already
    normalized to ``"F"`` / ``"C"`` by the caller.
    """
    if value_f is None:
        return None
    if temp_unit == "C":
        return (value_f - 32.0) / 1.8
    return value_f


def _pick_headline_row(rows: list) -> Optional[Any]:
    """Most-severe (then lowest device_id) weather reconciliation row, or None."""
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda r: (_BLOCKING_ORDER.get(r.blocking_level, 3), r.device_id),
    )[0]


def _weather_metric(row: Optional[Any], *, plane: bool) -> PerformanceContextWeatherMetric:
    """Project ONE reconciliation row into the compact metric block, verbatim.

    ``plane=True`` carries the irradiance plane; otherwise the temperature type.
    Every value is copied straight off the governed row — no label is invented,
    no state recomputed. ``used_by_active_model`` is always ``False`` (the
    weather→expected integration is deferred), per the data contract.
    """
    if row is None:
        return PerformanceContextWeatherMetric()
    return PerformanceContextWeatherMetric(
        label=row.state_label,
        plane=row.irradiance_plane if plane else None,
        type=None if plane else row.temperature_type,
        basis=row.declaration_basis,
        expected_model_eligible=bool(row.expected_model_eligible),
        used_by_active_model=False,
    )


def _pick_weather_rows(recon) -> tuple[Any, Any, Any]:
    """Select the headline / irradiance / temperature reconciliation rows.

    Shared by the compact ``weather_semantics`` projection AND the per-bucket
    provenance ``weather_declaration_mapping_id`` so both agree on which governed
    row backs each metric (never two different selections).
    """
    rows = list(recon.devices)
    headline = _pick_headline_row(rows)
    irr_row = next((r for r in rows if r.irradiance_plane is not None), headline)
    temp_row = next((r for r in rows if r.temperature_type is not None), headline)
    return headline, irr_row, temp_row


def _build_weather_semantics(
    db: Session, site, recon=None
) -> PerformanceContextWeatherSemantics:
    """Compose the verbatim weather-semantics block (compact + embedded rows).

    ``recon`` may be passed in by the caller to avoid recomputing the (read-only)
    reconciliation twice; when ``None`` it is built here.
    """
    if recon is None:
        recon = build_site_semantics_reconciliation(db, site)
    headline, irr_row, temp_row = _pick_weather_rows(recon)
    return PerformanceContextWeatherSemantics(
        irradiance=_weather_metric(irr_row, plane=True),
        temperature=_weather_metric(temp_row, plane=False),
        headline_state=headline.reconciliation_state if headline else None,
        blocking_level=headline.blocking_level if headline else None,
        reconciliation=recon,
    )


def _build_baseline_status(
    site,
    *,
    active,
    is_blocking: bool,
    report,
    result,
    window_expected_state: str,
) -> PerformanceContextBaselineStatus:
    """The active baseline's read-time health (validated on read, never mutated)."""
    selection_mode = getattr(result, "baseline_selection_mode", None) if result else None
    base = PerformanceContextBaselineStatus(
        expected_baseline_available=active is not None and not is_blocking,
        expected_state=window_expected_state,
        baseline_id=getattr(active, "id", None) if active is not None else None,
        baseline_type=(
            _enum_value(getattr(active, "baseline_type", None))
            if active is not None
            else None
        ),
        baseline_selection_mode=selection_mode,
    )
    if active is not None and is_blocking:
        meta = _baseline_invalid_meta(active, report)
        base.baseline_invalid = meta["baseline_invalid"]
        base.invalid_baseline_id = meta["invalid_baseline_id"]
        base.baseline_validation_summary = meta["baseline_validation_summary"]
        base.baseline_validation_policy_version = meta[
            "baseline_validation_policy_version"
        ]
        base.required_action = meta["required_action"]
    return base


def _build_telemetry_quality(db: Session, site) -> PerformanceContextTelemetryQuality:
    """Verbatim eligibility/mapping counts + verbatim health-projected freshness.

    Freshness is NOT re-derived here: it is the SAME verdict the
    ``/sites/{id}/health`` endpoint returns (``compute_site_telemetry_health``),
    projected onto the compact ``fresh``/``stale``/``no_data`` triplet. The
    health computation owns the last-data resolution (V2-native precedence) and
    the staleness thresholds; this service only maps and copies its result.
    """
    diag = compute_site_eligibility_diagnostics(db, site=site)
    latest_bucket_start = TelemetrySiteRollupCRUD(db).latest_bucket_start(site.id)

    health = compute_site_telemetry_health(db, site)
    latest_reading_at = _to_naive_utc(health.last_data_at)
    data_delay_minutes = health.data_delay_minutes
    freshness_state = _HEALTH_STATUS_TO_FRESHNESS.get(health.status, "no_data")

    return PerformanceContextTelemetryQuality(
        total_devices=diag.total_devices,
        mappable_count=diag.mappable_count,
        mapped_count=diag.mapped_count,
        unmapped_eligible_count=diag.unmapped_eligible_count,
        expected_driving_count=diag.expected_driving_count,
        weather_source_count=diag.weather_source_count,
        weather_unknown_semantics_count=diag.weather_unknown_semantics_count,
        latest_reading_at=latest_reading_at,
        latest_bucket_start=latest_bucket_start,
        data_delay_minutes=data_delay_minutes,
        freshness_state=freshness_state,
    )


def _actual_state(
    actual_value: Optional[float], eb, *, freshness_stale: bool
) -> str:
    """Per-bucket actual_state (0-vs-null integrity).

    A present value is ``available`` (a negative tare is a real reading) unless it
    is a literal ``0`` (``no_production_during_interval`` — the only state allowed
    to render a 0). A missing value is ``pre_pto`` when the aligned expected bucket
    is pre-PTO, else ``telemetry_stale`` when the site's latest reading is stale,
    else ``telemetry_unavailable``. Never fabricates a 0.
    """
    if actual_value is not None:
        if actual_value == 0:
            return ACTUAL_NO_PRODUCTION
        return ACTUAL_AVAILABLE
    if eb is not None and eb.status == BucketStatus.pre_pto:
        return ACTUAL_PRE_PTO
    if freshness_stale:
        return ACTUAL_TELEMETRY_STALE
    return ACTUAL_TELEMETRY_UNAVAILABLE


def build_performance_context(
    db: Session,
    *,
    site,
    window_start: datetime,
    window_end: datetime,
    bucket_size: str,
    temp_unit: str,
) -> PerformanceContextResponse:
    """Compose the read-only V2 performance-context envelope for a site.

    ``window_start``/``window_end`` are naive-UTC (already clamped by the route),
    ``bucket_size`` is one of the allowed sizes, and ``temp_unit`` is ``"F"``/``"C"``.
    Performs zero writes/commits.
    """
    tz_name = getattr(site, "timezone", None) or "UTC"
    bucket_hours = BUCKET_SIZE_TO_HOURS.get(bucket_size, 1.0)

    # --- Expected (verbatim period-effective calc), with the active-baseline
    # read-time validity guard mirrored from the chart builders: when the active
    # baseline is physically invalid the expected curve is SUPPRESSED entirely
    # (never fabricated) while actuals stay visible.
    active = _active_baseline(db, site.id)
    is_blocking, report = _evaluate_active_baseline(active)
    result = None
    if not is_blocking:
        result = compute_site_expected_period_effective(
            db,
            site=site,
            start=window_start,
            end=window_end,
            bucket_size=bucket_size,
        )
    expected_by_ts = {b.bucket_start: b for b in result.buckets} if result else {}
    selection_mode = getattr(result, "baseline_selection_mode", None) if result else None

    if is_blocking:
        window_expected_state = ExpectedState.baseline_invalid.value
        no_cover_state = ExpectedState.baseline_invalid.value
    elif result is None:
        window_expected_state = ExpectedState.baseline_not_available.value
        no_cover_state = ExpectedState.baseline_not_available.value
    else:
        window_expected_state = derive_expected_state(result).value
        # A timestamp with no covering baseline bucket is an honest gap region.
        no_cover_state = ExpectedState.baseline_not_available.value

    # --- Native rollup actuals (power / irradiance / cell temperature).
    rollup_crud = TelemetrySiteRollupCRUD(db)
    power_rows = rollup_crud.get_series(
        site_id=site.id,
        normalized_metric=SITE_POWER_METRIC,
        bucket_size=bucket_size,
        start=window_start,
        end=window_end,
    )
    irradiance_rows = rollup_crud.get_series(
        site_id=site.id,
        normalized_metric=IRRADIANCE_METRIC,
        bucket_size=bucket_size,
        start=window_start,
        end=window_end,
    )
    temperature_rows = rollup_crud.get_series(
        site_id=site.id,
        normalized_metric=CELL_TEMPERATURE_METRIC,
        bucket_size=bucket_size,
        start=window_start,
        end=window_end,
    )
    power_by_ts = {r.bucket_start: r for r in power_rows}
    irr_by_ts = {r.bucket_start: float(r.value) for r in irradiance_rows}
    temp_by_ts = {r.bucket_start: float(r.value) for r in temperature_rows}

    quality = _build_telemetry_quality(db, site)
    freshness_stale = quality.freshness_state == "stale"

    # Governed weather reconciliation, built ONCE (read-only) and reused for both
    # the compact weather_semantics projection and the per-bucket provenance
    # ``weather_declaration_mapping_id``. The governed mapping is a site-level
    # selection; per-bucket it is attached only when that bucket carries the
    # corresponding observed weather value (else null — never fabricated). There
    # is no per-bucket weather-source linkage in the telemetry rollups, so
    # ``irradiance_source_id``/``temperature_source_id`` stay null (honest).
    recon = build_site_semantics_reconciliation(db, site)
    _hl, _irr_recon_row, _temp_recon_row = _pick_weather_rows(recon)
    irr_mapping_id = getattr(_irr_recon_row, "mapping_id", None)
    temp_mapping_id = getattr(_temp_recon_row, "mapping_id", None)

    # Canonical, deterministic per-bucket axis: EVERY epoch-anchored bucket in
    # ``[window_start, window_end]`` gets exactly one point — not just the buckets
    # that happen to have a row. This is what lets a truly missing bucket surface
    # as ``actual_kw=null`` + an honest ``actual_state`` (never silently dropped).
    # The grid matches the rollup ``get_series`` bounds (``>= start``, ``<= end``)
    # and the expected calc grid exactly, so lookups align without borrowing.
    all_ts = expected_bucket_starts(window_start, window_end, bucket_size)

    series: list[PerformanceContextPoint] = []
    for ts in all_ts:
        eb = expected_by_ts.get(ts)
        power_row = power_by_ts.get(ts)
        has_irr = ts in irr_by_ts
        has_temp = ts in temp_by_ts

        actual_kw = float(power_row.value) if power_row is not None else None
        actual_kwh = actual_kw * bucket_hours if actual_kw is not None else None

        expected_kw = eb.expected_power_kw if eb is not None else None
        expected_kwh = eb.expected_energy_kwh if eb is not None else None
        baseline_id = eb.baseline_id if eb is not None else None

        variance_kwh = (
            actual_kwh - expected_kwh
            if actual_kwh is not None and expected_kwh is not None
            else None
        )
        variance_pct = calculate_actual_vs_expected(actual_kwh, expected_kwh)

        # Observed rolled-up weather ONLY (never the baseline's expected weather
        # input) — mixing sources would make provenance dishonest. Absent → null.
        irradiance = irr_by_ts.get(ts)
        temp_f = temp_by_ts.get(ts)

        expected_state = (
            _STATUS_TO_EXPECTED_STATE.get(eb.status, no_cover_state)
            if eb is not None
            else no_cover_state
        )

        # Provenance is copied verbatim from the rows that PRODUCED each value;
        # a field stays ``None`` when no producing row exists (never fabricated).
        provenance = PerformanceContextProvenance(
            actual_metric=SITE_POWER_METRIC if power_row is not None else None,
            actual_unit=power_row.unit if power_row is not None else None,
            actual_agg=power_row.agg if power_row is not None else None,
            expected_baseline_id=baseline_id,
            baseline_selection_mode=selection_mode if eb is not None else None,
            irradiance_metric=IRRADIANCE_METRIC if has_irr else None,
            # No per-bucket weather-source linkage exists in the telemetry rollups
            # that produced these observed means, so the source ids stay null
            # (absent provenance is null, never fabricated).
            irradiance_source_id=None,
            temperature_metric=CELL_TEMPERATURE_METRIC if has_temp else None,
            temperature_source_id=None,
            # Governed mapping backing the weather labels, attached only when this
            # bucket carries the corresponding observed value (else null).
            weather_declaration_mapping_id=(
                irr_mapping_id
                if has_irr
                else (temp_mapping_id if has_temp else None)
            ),
        )

        series.append(
            PerformanceContextPoint(
                bucket_start=ts,
                bucket_start_utc=ts,
                bucket_start_site_local=_site_local_dt(ts, tz_name),
                actual_kw=actual_kw,
                actual_kwh=actual_kwh,
                actual_state=_actual_state(
                    actual_kw, eb, freshness_stale=freshness_stale
                ),
                expected_kw=expected_kw,
                expected_kwh=expected_kwh,
                expected_state=expected_state,
                baseline_id=baseline_id,
                variance_kwh=variance_kwh,
                variance_pct=variance_pct,
                irradiance_wm2=irradiance,
                temperature=_convert_temp(temp_f, temp_unit),
                sample_count=power_row.sample_count if power_row is not None else None,
                completeness=(
                    float(power_row.completeness)
                    if power_row is not None and power_row.completeness is not None
                    else None
                ),
                source_provenance=provenance,
            )
        )

    # --- Window summary (honest, never fabricated). The percent is computed ONLY
    # over the comparable subset (buckets that have BOTH an actual and an expected
    # energy) so it compares like-for-like; the totals are informational sums.
    actual_kwh_values = [p.actual_kwh for p in series if p.actual_kwh is not None]
    expected_kwh_values = [p.expected_kwh for p in series if p.expected_kwh is not None]
    total_actual_kwh = sum(actual_kwh_values) if actual_kwh_values else None
    total_expected_kwh = sum(expected_kwh_values) if expected_kwh_values else None

    comp_actual = 0.0
    comp_expected = 0.0
    comp_count = 0
    for p in series:
        if p.actual_kwh is not None and p.expected_kwh is not None:
            comp_actual += p.actual_kwh
            comp_expected += p.expected_kwh
            comp_count += 1
    summary_variance_kwh = comp_actual - comp_expected if comp_count else None
    summary_variance_pct = (
        calculate_actual_vs_expected(comp_actual, comp_expected) if comp_count else None
    )

    n_actual = sum(1 for p in series if p.actual_kw is not None)
    if n_actual == 0:
        summary_actual_state = (
            ACTUAL_TELEMETRY_STALE if freshness_stale else ACTUAL_TELEMETRY_UNAVAILABLE
        )
    elif n_actual == len(series):
        summary_actual_state = ACTUAL_AVAILABLE
    else:
        summary_actual_state = ACTUAL_PARTIAL

    summary = PerformanceContextSummary(
        window_start=window_start,
        window_end=window_end,
        bucket_size=bucket_size,
        temp_unit=temp_unit,
        bucket_count=len(series),
        total_actual_kwh=total_actual_kwh,
        total_expected_kwh=total_expected_kwh,
        variance_kwh=summary_variance_kwh,
        variance_pct=summary_variance_pct,
        actual_state=summary_actual_state,
        expected_state=window_expected_state,
    )

    weather_semantics = _build_weather_semantics(db, site, recon=recon)

    # --- Additive native observed-weather indicator (cosmetic, composition-only).
    # Derived from the SAME already-fetched rollups (latest non-null irradiance +
    # cell temperature), native freshness, and the GOVERNED plane flag — no new
    # query, no physics, no baseline. ``derive_site_condition`` preserves the
    # ``null``-vs-``0`` rule and never labels POA unless the plane is governed.
    latest_irr_ts = max(irr_by_ts) if irr_by_ts else None
    latest_irr_value = irr_by_ts.get(latest_irr_ts) if latest_irr_ts is not None else None
    latest_temp_ts = max(temp_by_ts) if temp_by_ts else None
    latest_temp_value = temp_by_ts.get(latest_temp_ts) if latest_temp_ts is not None else None
    governed_temp_type = weather_semantics.temperature.type
    if governed_temp_type in (None, "unknown"):
        governed_temp_type = None
    observed_condition = derive_site_condition(
        latest_irradiance_wm2=latest_irr_value,
        latest_irradiance_at_utc=latest_irr_ts,
        freshness_state=quality.freshness_state,
        timezone_name=tz_name,
        coordinates=parse_lon_lat(getattr(site, "lon_lat_url", None)),
        plane_governed=(weather_semantics.irradiance.plane or "").lower() == "poa",
        latest_temperature_f=latest_temp_value,
        temperature_unit=temp_unit,
        temperature_type=governed_temp_type,
    )

    return PerformanceContextResponse(
        site_id=site.id,
        site_timezone=tz_name,
        window=PerformanceContextWindow(start=window_start, end=window_end),
        window_start=window_start,
        window_end=window_end,
        bucket_size=bucket_size,
        temp_unit=temp_unit,
        series=series,
        weather_semantics=weather_semantics,
        observed_condition=observed_condition,
        baseline_status=_build_baseline_status(
            site,
            active=active,
            is_blocking=is_blocking,
            report=report,
            result=result,
            window_expected_state=window_expected_state,
        ),
        telemetry_quality=quality,
        summary=summary,
    )
