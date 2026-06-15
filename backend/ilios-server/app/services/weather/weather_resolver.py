"""W1 — WeatherResolver over EXISTING DAS weather only.

This is the first runtime consumer of the W0 weather provenance foundation. It
resolves the two physics inputs the weather-adjusted expected calc needs —
plane-of-array irradiance (``W/m^2``) and cell temperature (``degF``) — for a
site + window + bucket size, reading ONLY the existing V2 telemetry interval
rollups (``telemetry_site_interval_rollups`` via
:meth:`TelemetrySiteRollupCRUD.get_series`) and CARRYING provenance metadata
derived from the W0 weather domain:

* ``weather_device_mappings`` — declared measurement semantics (irradiance plane,
  temperature type, calibration status, optional source) of a telemetry stream;
* ``weather_source_profiles`` — the effective-dated governing policy for a site;
* ``weather_sources`` — source identity (label, confidence, modeled flag).

Strict W1 contract (mirrors the W0 invariants in ``app/models/weather.py``):

* **READ-ONLY.** No writes — not even to ``expected_weather_provenance`` (that
  snapshot is deferred to W2). No provider/credential calls, no secrets, no
  BigQuery/Firestore/legacy references.
* **The NUMBERS are the existing DAS rollup values, untouched.** The resolver
  does NOT transpose GHI/DNI/DHI → POA, does NOT convert ambient → cell/module,
  and never fabricates a value. Because it returns exactly the same
  irradiance/cell-temp values the previous direct reads produced, the downstream
  expected math is byte-for-byte identical (see ``compute_site_expected``).
* **Semantics are explicit and never guessed.** Values are labelled
  ``semantics_verified`` ONLY when a W0 device mapping explicitly declares POA
  irradiance AND a cell/module/modeled-cell temperature. Otherwise the values are
  still passed through (to preserve current behaviour) under the explicit
  ``legacy_das_unverified`` status with ``unknown`` plane/temperature/confidence —
  an unknown stream is NEVER promoted to high-confidence POA.

The provenance ``source_type``/``is_modeled`` describe how the NUMERIC VALUES
were produced. In W1 the values always come from the DAS telemetry stream, so
when no measured source is mapped the attribution stays
``das_provider_stream`` / not-modeled. A profile that *references* a modeled
source is governance configuration — it never causes W1 to claim the values are
modeled (that would be misattribution).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.telemetry_native import TelemetrySiteRollupCRUD
from app.crud.weather import (
    WeatherDeviceMappingCRUD,
    WeatherObservationCRUD,
    WeatherSourceCRUD,
    WeatherSourceProfileCRUD,
)
from app.models.weather import (
    WeatherCalibrationStatus,
    WeatherConfidence,
    WeatherIrradiancePlane,
    WeatherSourceProfileRole,
    WeatherSourceProfileStatus,
    WeatherSourceType,
    WeatherTemperatureType,
)
from app.services.weather.bucketing import (
    bucket_observations,
    expected_bucket_starts,
    min_confidence,
)

logger = logging.getLogger(__name__)

# Normalized rollup metric keys (must match expected_service + the metric catalog).
IRRADIANCE_METRIC = "irradiance_wm2"
CELL_TEMPERATURE_METRIC = "cell_temperature_f"

# Temperature types that ARE usable as cell temperature in the physics (W1 does
# NOT convert ambient → cell, so ``ambient`` is intentionally excluded).
CELL_USABLE_TEMPERATURE_TYPES = frozenset(
    {
        WeatherTemperatureType.cell.value,
        WeatherTemperatureType.module.value,
        WeatherTemperatureType.modeled_cell.value,
    }
)

# Coarse confidence ordering used for the profile min-confidence policy check.
_CONFIDENCE_RANK = {
    WeatherConfidence.unknown.value: 0,
    WeatherConfidence.low.value: 1,
    WeatherConfidence.medium.value: 2,
    WeatherConfidence.high.value: 3,
}


class WeatherResolverStatus(str, Enum):
    """Overall outcome of resolving weather provenance for a window."""

    semantics_verified = "semantics_verified"
    legacy_das_unverified = "legacy_das_unverified"
    no_weather = "no_weather"


# ``missing_inputs`` keys — gaps in trustworthy provenance/availability for the
# window. NOTE: this is the *provenance* missing-inputs list and is distinct from
# the per-bucket ``BucketStatus.missing_inputs`` in ``expected_service`` (which
# is about an individual bucket lacking a numeric value).
MISSING_IRRADIANCE = "missing_irradiance"
MISSING_CELL_TEMPERATURE = "missing_cell_temperature"
SEMANTICS_UNKNOWN = "semantics_unknown"
PROFILE_MISSING = "profile_missing"
WEATHER_SOURCE_UNAPPROVED = "weather_source_unapproved"
BELOW_CONFIDENCE_THRESHOLD = "below_confidence_threshold"

# ``warnings`` keys — non-fatal provenance observations.
WARN_SEMANTICS_CONFLICT = "semantics_conflict"
WARN_LEGACY_DAS_UNVERIFIED = "legacy_das_unverified"
WARN_PROFILE_PARTIAL_WINDOW = "profile_partial_window"

# ``indicators`` keys — glossary keys the FE can render as "why" tooltips.
IND_MISSING_IRRADIANCE = "missing_irradiance"
IND_MISSING_CELL_TEMPERATURE = "missing_cell_temperature"
IND_SEMANTICS_UNKNOWN = "semantics_unknown"
IND_WHY_UNVERIFIED = "why_unverified"
IND_CONFIDENCE_UNKNOWN = "confidence_unknown"
IND_PROFILE_MISSING = "profile_missing"
IND_WEATHER_SOURCE_UNAPPROVED = "weather_source_unapproved"
IND_BELOW_CONFIDENCE_THRESHOLD = "below_confidence_threshold"
IND_MODELED_NOT_AVAILABLE = "modeled_not_available"

# W2 historical-path keys (used only when an approved historical profile drives
# the window from imported observations; the DAS path never sets these).
WARN_HISTORICAL_PARTIAL_WINDOW = "historical_partial_window"
IND_HISTORICAL_WEATHER_ACTIVE = "historical_weather_active"
IND_MODELED_WEATHER_PRESENT = "modeled_weather_present"
IND_COVERAGE_GAPS_PRESENT = "coverage_gaps_present"


# ---------------------------------------------------------------------------
# Result dataclasses (immutable)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ResolvedWeatherBucket:
    """One resolved weather bucket. ``bucket_start`` is naive-UTC.

    Values are the existing DAS rollup values, unchanged. ``None`` means the
    series had no row for that bucket (never zero-filled).
    """

    bucket_start: datetime
    irradiance_poa_wm2: Optional[float]
    cell_temperature_f: Optional[float]


@dataclass(frozen=True)
class ResolvedWeatherProvenance:
    """Window-level provenance describing what drove the resolved weather.

    ``source_type``/``is_modeled`` describe how the numeric VALUES were produced
    (always the DAS stream in W1). ``weather_source_id``/``profile_id`` are
    contextual references to the configured W0 governance, when present.
    """

    status: str
    source_type: str
    source_label: str
    is_modeled: bool
    confidence: str
    irradiance_plane: str
    temperature_type: str
    calibration_status: str
    weather_source_id: Optional[int] = None
    profile_id: Optional[int] = None
    profile_role: Optional[str] = None
    min_confidence_policy: Optional[str] = None
    missing_inputs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    indicators: tuple[str, ...] = ()
    # W2 additive fields. The DAS path leaves these at their defaults so its
    # provenance is unchanged; the historical path sets them to disclose that the
    # values came from approved imported observations.
    observation_batch_ids: tuple[int, ...] = ()
    historical: bool = False
    coverage_pct: Optional[float] = None


@dataclass(frozen=True)
class ResolvedWeatherWindow:
    """Resolved weather buckets for a window plus the accompanying provenance."""

    buckets: dict[datetime, ResolvedWeatherBucket]
    provenance: ResolvedWeatherProvenance


@dataclass(frozen=True)
class _MetricSemantics:
    """Resolved semantics for one rollup metric over the window.

    ``chosen`` is the mapping used for source/calibration surfacing (the most
    recently effective overlapping mapping that declares the semantic value, else
    the most recent overlapping mapping of any value). ``value`` is the resolved
    plane / temperature-type (``unknown`` when none declared or on conflict).
    """

    chosen: Optional[object]
    value: str
    conflict: bool


# ---------------------------------------------------------------------------
# Pure helpers (no DB — fully unit-testable)
# ---------------------------------------------------------------------------
def _enum_value(value) -> Optional[str]:
    """Return ``value.value`` for an Enum, the string itself otherwise, ``None`` passthrough."""
    if value is None:
        return None
    return value.value if hasattr(value, "value") else value


def _covers_window(eff_from, eff_to, start: datetime, end: datetime) -> bool:
    """True if ``[eff_from, eff_to]`` fully covers ``[start, end]`` (None = open)."""
    return (eff_from is None or eff_from <= start) and (eff_to is None or eff_to >= end)


def _overlaps_window(eff_from, eff_to, start: datetime, end: datetime) -> bool:
    """True if ``[eff_from, eff_to]`` overlaps ``[start, end]`` at all (None = open)."""
    return (eff_from is None or eff_from <= end) and (eff_to is None or eff_to >= start)


def _periods_cover_window(periods, start: datetime, end: datetime) -> bool:
    """True if the UNION of ``periods`` (list of ``(eff_from, eff_to)``) fully
    covers ``[start, end]``. ``None`` bounds are treated as open (-inf / +inf).

    Used to keep ``semantics_verified`` conservative: a mapping that only
    partially overlaps the window must NOT verify the whole window, otherwise an
    unmapped sub-range would be silently promoted to POA/cell semantics.
    """
    if not periods:
        return False
    norm = sorted(
        ((ef or datetime.min, et or datetime.max) for ef, et in periods),
        key=lambda p: p[0],
    )
    cursor = start
    for ef, et in norm:
        if ef > cursor:
            return False  # gap before the next period begins
        if et > cursor:
            cursor = et
        if cursor >= end:
            return True
    return cursor >= end


def _confidence_rank(confidence: Optional[str]) -> int:
    """Coarse numeric rank for a confidence band (unknown=0 .. high=3)."""
    return _CONFIDENCE_RANK.get(confidence or WeatherConfidence.unknown.value, 0)


def _mapping_sort_key(mapping) -> tuple:
    """Deterministic recency key: latest ``effective_from`` wins, tie-break by id."""
    return (mapping.effective_from or datetime.min, mapping.id)


def _resolve_metric_mappings(
    mappings: list,
    *,
    metric: str,
    attr: str,
    start: datetime,
    end: datetime,
) -> _MetricSemantics:
    """Resolve the semantic value (plane or temperature type) for one metric.

    Considers only mappings whose ``metric`` matches and whose effective period
    overlaps the window. A non-``unknown`` value is only resolved (i.e. eligible
    to drive ``semantics_verified``) when ALL of the following hold —
    deliberately conservative so an unknown sub-range is never promoted:

    * exactly one distinct non-``unknown`` value is declared (two or more distinct
      values is a conflict, resolved ``unknown``);
    * the declaring mappings' effective periods FULLY COVER the window (a mapping
      that only partially overlaps must not verify the whole window);
    * no overlapping mapping leaves the semantics ambiguous — i.e. there is no
      coexisting ``unknown``-valued mapping for the same metric (the site-level
      rollup could otherwise be driven by the unmapped stream).

    When a single value is declared but coverage is partial or an ambiguous
    ``unknown`` mapping coexists, the ``chosen`` mapping is still surfaced (for
    source/calibration context) but ``value`` stays ``unknown`` so the window
    resolves as ``legacy_das_unverified``, not ``semantics_verified``.
    """
    candidates = [
        m
        for m in mappings
        if m.metric == metric
        and _overlaps_window(m.effective_from, m.effective_to, start, end)
    ]
    if not candidates:
        return _MetricSemantics(chosen=None, value="unknown", conflict=False)

    most_recent = max(candidates, key=_mapping_sort_key)
    declaring = [m for m in candidates if _enum_value(getattr(m, attr)) != "unknown"]
    distinct = {_enum_value(getattr(m, attr)) for m in declaring}

    if len(distinct) > 1:
        return _MetricSemantics(chosen=most_recent, value="unknown", conflict=True)
    if len(distinct) == 1:
        chosen = max(declaring, key=_mapping_sort_key)
        has_unknown_overlap = len(declaring) < len(candidates)
        fully_covered = _periods_cover_window(
            [(m.effective_from, m.effective_to) for m in declaring], start, end
        )
        if fully_covered and not has_unknown_overlap:
            return _MetricSemantics(
                chosen=chosen, value=next(iter(distinct)), conflict=False
            )
        # Partial coverage or an ambiguous unknown overlap: keep context, but do
        # NOT verify — the window stays unverified rather than over-promoted.
        return _MetricSemantics(chosen=chosen, value="unknown", conflict=False)
    return _MetricSemantics(chosen=most_recent, value="unknown", conflict=False)


def _select_active_profile(
    profiles: list, start: datetime, end: datetime
) -> tuple[Optional[object], bool, bool]:
    """Pick the governing profile for the window from a site's profiles.

    ``profiles`` is expected ordered by ``priority`` desc then ``id`` asc (as the
    CRUD returns it). Prefers an ``active`` profile that fully covers the window;
    falls back to an ``active`` profile that merely overlaps it (flagged
    ``partial``). Returns ``(profile_or_None, partial_window, has_unapproved)``
    where ``has_unapproved`` means profiles exist for the site but none is active.
    """
    active = [
        p
        for p in profiles
        if _enum_value(p.status) == WeatherSourceProfileStatus.active.value
    ]
    has_unapproved = bool(profiles) and not active

    covering = [
        p for p in active if _covers_window(p.effective_from, p.effective_to, start, end)
    ]
    if covering:
        return covering[0], False, has_unapproved

    overlapping = [
        p
        for p in active
        if _overlaps_window(p.effective_from, p.effective_to, start, end)
    ]
    if overlapping:
        return overlapping[0], True, has_unapproved

    return None, False, has_unapproved


def _dedupe(items: list[str]) -> tuple[str, ...]:
    """Order-preserving de-duplication into a tuple."""
    seen: dict[str, None] = {}
    for it in items:
        seen.setdefault(it, None)
    return tuple(seen.keys())


def derive_weather_provenance(
    *,
    irr_sem: _MetricSemantics,
    temp_sem: _MetricSemantics,
    active_profile: Optional[object],
    profile_partial_window: bool,
    has_unapproved_profile: bool,
    value_source: Optional[object],
    has_irradiance: bool,
    has_cell_temperature: bool,
) -> ResolvedWeatherProvenance:
    """Pure provenance derivation (no DB).

    Decides the resolver status and assembles the provenance disclosure. The key
    safety rule: values are labelled ``semantics_verified`` ONLY when a mapping
    explicitly declares POA irradiance AND a cell/module/modeled-cell
    temperature with no conflict; otherwise the values still pass through under
    ``legacy_das_unverified`` with ``unknown`` semantics — never promoted to POA
    or to a higher confidence.
    """
    missing: list[str] = []
    warnings: list[str] = []
    indicators: list[str] = []

    # Whole-series availability (distinct from per-bucket gaps).
    if not has_irradiance:
        missing.append(MISSING_IRRADIANCE)
        indicators.append(IND_MISSING_IRRADIANCE)
    if not has_cell_temperature:
        missing.append(MISSING_CELL_TEMPERATURE)
        indicators.append(IND_MISSING_CELL_TEMPERATURE)

    if irr_sem.conflict or temp_sem.conflict:
        warnings.append(WARN_SEMANTICS_CONFLICT)

    irradiance_is_poa = irr_sem.value == WeatherIrradiancePlane.poa.value
    temperature_is_cell = temp_sem.value in CELL_USABLE_TEMPERATURE_TYPES
    verified = (
        irradiance_is_poa
        and temperature_is_cell
        and not irr_sem.conflict
        and not temp_sem.conflict
    )

    if not has_irradiance and not has_cell_temperature:
        status = WeatherResolverStatus.no_weather.value
    elif verified:
        status = WeatherResolverStatus.semantics_verified.value
    else:
        status = WeatherResolverStatus.legacy_das_unverified.value

    # Calibration status surfaced from whichever mapping carries it.
    calibration_status = (
        _enum_value(getattr(irr_sem.chosen, "calibration_status", None))
        or _enum_value(getattr(temp_sem.chosen, "calibration_status", None))
        or WeatherCalibrationStatus.unknown.value
    )

    if verified:
        irradiance_plane = WeatherIrradiancePlane.poa.value
        temperature_type = temp_sem.value
        # Confidence comes from the MAPPED measured source only — never silently
        # upgraded from calibration. No mapped source => unknown (honest).
        if value_source is not None:
            confidence = _enum_value(value_source.default_confidence)
            source_type = _enum_value(value_source.source_type)
            is_modeled = bool(value_source.is_modeled)
            source_label = value_source.display_name
            weather_source_id = value_source.id
        else:
            confidence = WeatherConfidence.unknown.value
            source_type = WeatherSourceType.das_provider_stream.value
            is_modeled = False
            source_label = "DAS telemetry stream (verified semantics)"
            weather_source_id = None
    else:
        # Unverified / legacy: pass values through but NEVER promote to POA or to
        # a higher-than-unknown confidence. Value attribution stays DAS.
        irradiance_plane = WeatherIrradiancePlane.unknown.value
        temperature_type = WeatherTemperatureType.unknown.value
        confidence = WeatherConfidence.unknown.value
        source_type = WeatherSourceType.das_provider_stream.value
        is_modeled = False
        source_label = "DAS telemetry stream (unverified semantics)"
        weather_source_id = value_source.id if value_source is not None else None
        if status == WeatherResolverStatus.legacy_das_unverified.value:
            warnings.append(WARN_LEGACY_DAS_UNVERIFIED)
            missing.append(SEMANTICS_UNKNOWN)
            indicators.append(IND_SEMANTICS_UNKNOWN)
            indicators.append(IND_WHY_UNVERIFIED)

    if confidence == WeatherConfidence.unknown.value:
        indicators.append(IND_CONFIDENCE_UNKNOWN)

    # Governing profile policy.
    if active_profile is not None:
        profile_id = active_profile.id
        profile_role = _enum_value(active_profile.role)
        min_confidence_policy = _enum_value(active_profile.min_confidence_policy)
        if profile_partial_window:
            warnings.append(WARN_PROFILE_PARTIAL_WINDOW)
        if min_confidence_policy is not None and _confidence_rank(
            confidence
        ) < _confidence_rank(min_confidence_policy):
            missing.append(BELOW_CONFIDENCE_THRESHOLD)
            indicators.append(IND_BELOW_CONFIDENCE_THRESHOLD)
        # A profile permitting modeled fallback while W1 resolves DAS only.
        if getattr(active_profile, "external_modeled_allowed", False):
            indicators.append(IND_MODELED_NOT_AVAILABLE)
    else:
        profile_id = None
        profile_role = None
        min_confidence_policy = None
        missing.append(PROFILE_MISSING)
        indicators.append(IND_PROFILE_MISSING)
        if has_unapproved_profile:
            missing.append(WEATHER_SOURCE_UNAPPROVED)
            warnings.append(WEATHER_SOURCE_UNAPPROVED)
            indicators.append(IND_WEATHER_SOURCE_UNAPPROVED)

    return ResolvedWeatherProvenance(
        status=status,
        source_type=source_type,
        source_label=source_label,
        is_modeled=is_modeled,
        confidence=confidence,
        irradiance_plane=irradiance_plane,
        temperature_type=temperature_type,
        calibration_status=calibration_status,
        weather_source_id=weather_source_id,
        profile_id=profile_id,
        profile_role=profile_role,
        min_confidence_policy=min_confidence_policy,
        missing_inputs=_dedupe(missing),
        warnings=_dedupe(warnings),
        indicators=_dedupe(indicators),
    )


def derive_historical_provenance(
    *,
    bucketed,
    source: Optional[object],
    profile: object,
    profile_partial_window: bool,
    coverage_pct: float,
) -> ResolvedWeatherProvenance:
    """Pure provenance for the W2 historical path (no DB).

    Values come exclusively from APPROVED imported observations whose semantics
    are EXPLICIT (only POA irradiance / cell-usable temperature rows survive the
    bucketing usable-filter) — that is precisely what makes the window
    ``semantics_verified`` without any conversion. Strict W2 disclosure:

    * a physics input absent from the window is reported via ``missing_inputs``
      (and a matching indicator), never fabricated or back-filled;
    * modeled data is flagged (``is_modeled`` + ``modeled_weather_present``) but
      never hidden or treated as measured;
    * confidence is the MOST CONSERVATIVE band across the mapped source default
      and the observed rows — never silently upgraded;
    * ``calibration_status`` stays ``unknown`` (W2 performs no calibration);
    * the additive ``historical`` / ``observation_batch_ids`` / ``coverage_pct``
      fields make the provenance auditable back to the exact import batches.
    """
    aggs = list(bucketed.buckets.values())
    has_irradiance = any(a.irradiance_poa_wm2 is not None for a in aggs)
    has_cell_temperature = any(a.cell_temperature_f is not None for a in aggs)

    irr_modeled = any(
        a.irradiance_poa_wm2 is not None and a.irradiance_modeled for a in aggs
    )
    temp_modeled = any(
        a.cell_temperature_f is not None and a.cell_temperature_modeled for a in aggs
    )
    source_modeled = bool(getattr(source, "is_modeled", False))
    is_modeled = source_modeled or irr_modeled or temp_modeled

    bands: list[Optional[str]] = [
        _enum_value(getattr(source, "default_confidence", None))
    ]
    for a in aggs:
        if a.irradiance_poa_wm2 is not None:
            bands.append(a.irradiance_confidence)
        if a.cell_temperature_f is not None:
            bands.append(a.cell_temperature_confidence)
    confidence = min_confidence(bands) or WeatherConfidence.unknown.value

    irradiance_plane = (
        WeatherIrradiancePlane.poa.value
        if has_irradiance
        else WeatherIrradiancePlane.unknown.value
    )
    temperature_type = (
        (
            WeatherTemperatureType.modeled_cell.value
            if temp_modeled
            else WeatherTemperatureType.cell.value
        )
        if has_cell_temperature
        else WeatherTemperatureType.unknown.value
    )

    missing: list[str] = []
    warnings: list[str] = []
    indicators: list[str] = [IND_HISTORICAL_WEATHER_ACTIVE]

    if not has_irradiance:
        missing.append(MISSING_IRRADIANCE)
        indicators.append(IND_MISSING_IRRADIANCE)
    if not has_cell_temperature:
        missing.append(MISSING_CELL_TEMPERATURE)
        indicators.append(IND_MISSING_CELL_TEMPERATURE)

    if profile_partial_window:
        warnings.append(WARN_HISTORICAL_PARTIAL_WINDOW)

    if is_modeled:
        indicators.append(IND_MODELED_WEATHER_PRESENT)
    if coverage_pct < 1.0:
        indicators.append(IND_COVERAGE_GAPS_PRESENT)
    if confidence == WeatherConfidence.unknown.value:
        indicators.append(IND_CONFIDENCE_UNKNOWN)

    min_confidence_policy = _enum_value(
        getattr(profile, "min_confidence_policy", None)
    )
    if min_confidence_policy is not None and _confidence_rank(
        confidence
    ) < _confidence_rank(min_confidence_policy):
        missing.append(BELOW_CONFIDENCE_THRESHOLD)
        indicators.append(IND_BELOW_CONFIDENCE_THRESHOLD)

    if source is not None:
        source_type = _enum_value(source.source_type)
        source_label = source.display_name
        weather_source_id = source.id
    else:
        # Defensive: a historical profile always references a source, but never
        # crash provenance if the row was removed out from under us.
        source_type = WeatherSourceType.imported_historical_provider_file.value
        source_label = "Imported historical weather"
        weather_source_id = getattr(profile, "weather_source_id", None)

    return ResolvedWeatherProvenance(
        status=WeatherResolverStatus.semantics_verified.value,
        source_type=source_type,
        source_label=source_label,
        is_modeled=is_modeled,
        confidence=confidence,
        irradiance_plane=irradiance_plane,
        temperature_type=temperature_type,
        calibration_status=WeatherCalibrationStatus.unknown.value,
        weather_source_id=weather_source_id,
        profile_id=profile.id,
        profile_role=_enum_value(profile.role),
        min_confidence_policy=min_confidence_policy,
        missing_inputs=_dedupe(missing),
        warnings=_dedupe(warnings),
        indicators=_dedupe(indicators),
        observation_batch_ids=bucketed.batch_ids,
        historical=True,
        coverage_pct=coverage_pct,
    )


# ---------------------------------------------------------------------------
# Resolver (DB wrapper — read-only)
# ---------------------------------------------------------------------------
class WeatherResolver:
    """Resolves weather physics inputs + provenance for a site window (read-only).

    All DB access is through existing read CRUD helpers; the resolver never
    mutates state and performs no external/provider/secret/BigQuery/Firestore
    calls.
    """

    def __init__(self, db: Session):
        self._db = db

    def resolve_window(
        self,
        *,
        site_id: int,
        start: datetime,
        end: datetime,
        bucket_size: str = "1h",
    ) -> ResolvedWeatherWindow:
        """Resolve irradiance + cell-temperature buckets and provenance.

        Selection rule: when an ACTIVE ``role=historical`` profile governs the
        window AND physics-usable imported observations exist for it (W2), the
        window is resolved from those approved observations. In every other case
        — including no historical profile, a draft/rejected one, or one with no
        usable observations — the resolver falls through to the EXISTING live-DAS
        path, which is byte-for-byte identical to W1.
        """
        profiles = WeatherSourceProfileCRUD(self._db).list_for_site(site_id)
        historical_profile, partial_window, _ = _select_active_profile(
            [
                p
                for p in profiles
                if _enum_value(p.role) == WeatherSourceProfileRole.historical.value
            ],
            start,
            end,
        )
        if historical_profile is not None:
            historical = self._resolve_historical_window(
                site_id=site_id,
                start=start,
                end=end,
                bucket_size=bucket_size,
                profile=historical_profile,
                profile_partial_window=partial_window,
            )
            if historical is not None:
                return historical

        return self._resolve_das_window(
            site_id=site_id,
            start=start,
            end=end,
            bucket_size=bucket_size,
            profiles=profiles,
        )

    def _resolve_das_window(
        self,
        *,
        site_id: int,
        start: datetime,
        end: datetime,
        bucket_size: str,
        profiles: list,
    ) -> ResolvedWeatherWindow:
        """The W1 live-DAS resolution, unchanged.

        The bucket set is exactly the union of the irradiance and cell-temp
        rollup buckets present in the window (never invented, never zero-filled),
        with values equal to ``float(row.value)`` — identical to the legacy
        direct reads so the downstream expected numbers are unchanged. ``profiles``
        is passed in (already fetched by :meth:`resolve_window`) to avoid a
        redundant read; the resolution is otherwise identical to W1.
        """
        rollups = TelemetrySiteRollupCRUD(self._db)
        irradiance_rows = rollups.get_series(
            site_id=site_id,
            normalized_metric=IRRADIANCE_METRIC,
            bucket_size=bucket_size,
            start=start,
            end=end,
        )
        cell_temp_rows = rollups.get_series(
            site_id=site_id,
            normalized_metric=CELL_TEMPERATURE_METRIC,
            bucket_size=bucket_size,
            start=start,
            end=end,
        )

        irradiance_map = {r.bucket_start: float(r.value) for r in irradiance_rows}
        cell_temp_map = {r.bucket_start: float(r.value) for r in cell_temp_rows}

        buckets = {
            bs: ResolvedWeatherBucket(
                bucket_start=bs,
                irradiance_poa_wm2=irradiance_map.get(bs),
                cell_temperature_f=cell_temp_map.get(bs),
            )
            for bs in sorted(set(irradiance_map) | set(cell_temp_map))
        }

        mappings = WeatherDeviceMappingCRUD(self._db).list_for_site(site_id)

        irr_sem = _resolve_metric_mappings(
            mappings,
            metric=IRRADIANCE_METRIC,
            attr="irradiance_plane",
            start=start,
            end=end,
        )
        temp_sem = _resolve_metric_mappings(
            mappings,
            metric=CELL_TEMPERATURE_METRIC,
            attr="temperature_type",
            start=start,
            end=end,
        )

        # Historical-role profiles are a W2 concept and must NEVER influence the
        # live DAS provenance. When the historical path declines (no active
        # profile, or no usable observations) and we fall back here, the DAS
        # resolution must behave exactly as W1 did — i.e. as if historical
        # profiles did not exist. Excluding them keeps active-profile selection
        # and `has_unapproved` byte-identical to W1 even if a draft/active-but-
        # unusable historical profile happens to overlap the window.
        das_governing_profiles = [
            p
            for p in profiles
            if _enum_value(p.role) != WeatherSourceProfileRole.historical.value
        ]
        active_profile, profile_partial_window, has_unapproved = _select_active_profile(
            das_governing_profiles, start, end
        )

        value_source = self._resolve_value_source(irr_sem, temp_sem)

        provenance = derive_weather_provenance(
            irr_sem=irr_sem,
            temp_sem=temp_sem,
            active_profile=active_profile,
            profile_partial_window=profile_partial_window,
            has_unapproved_profile=has_unapproved,
            value_source=value_source,
            has_irradiance=bool(irradiance_map),
            has_cell_temperature=bool(cell_temp_map),
        )

        return ResolvedWeatherWindow(buckets=buckets, provenance=provenance)

    def _resolve_historical_window(
        self,
        *,
        site_id: int,
        start: datetime,
        end: datetime,
        bucket_size: str,
        profile: object,
        profile_partial_window: bool,
    ) -> Optional[ResolvedWeatherWindow]:
        """Resolve a window from APPROVED imported historical observations.

        Reads only the governing historical profile's source observations for the
        two physics metrics, buckets them onto the SAME epoch-anchored grid the
        rollups/expected calc use (so values slot in without a separate replay
        engine), and emits buckets ONLY where a usable value exists (never
        zero-filled). Returns ``None`` — so the caller falls back to the W1 DAS
        path — when there is no physics-usable observation in the window, so the
        resolver never downgrades a live window to an empty historical one.
        """
        observations = WeatherObservationCRUD(self._db).get_window(
            site_id,
            start=start,
            end=end,
            metrics=[IRRADIANCE_METRIC, CELL_TEMPERATURE_METRIC],
            weather_source_id=profile.weather_source_id,
        )
        bucketed = bucket_observations(
            observations,
            bucket_size=bucket_size,
            irradiance_metric=IRRADIANCE_METRIC,
            cell_temperature_metric=CELL_TEMPERATURE_METRIC,
        )

        buckets = {
            bs: ResolvedWeatherBucket(
                bucket_start=bs,
                irradiance_poa_wm2=agg.irradiance_poa_wm2,
                cell_temperature_f=agg.cell_temperature_f,
            )
            for bs, agg in bucketed.buckets.items()
            if agg.irradiance_poa_wm2 is not None
            or agg.cell_temperature_f is not None
        }
        if not buckets:
            return None  # no usable historical data → fall back to the DAS path

        grid = expected_bucket_starts(start, end, bucket_size)
        total = len(grid)
        both_usable = sum(
            1
            for bs in grid
            if (agg := bucketed.buckets.get(bs)) is not None
            and agg.irradiance_poa_wm2 is not None
            and agg.cell_temperature_f is not None
        )
        coverage_pct = round(both_usable / total, 4) if total else 0.0

        source = WeatherSourceCRUD(self._db).get(profile.weather_source_id)
        provenance = derive_historical_provenance(
            bucketed=bucketed,
            source=source,
            profile=profile,
            profile_partial_window=profile_partial_window,
            coverage_pct=coverage_pct,
        )
        return ResolvedWeatherWindow(buckets=buckets, provenance=provenance)

    def _resolve_value_source(
        self, irr_sem: _MetricSemantics, temp_sem: _MetricSemantics
    ) -> Optional[object]:
        """Load the measured source that produced the values (irradiance first).

        Read-only: prefers the irradiance mapping's source, then the temperature
        mapping's source. Returns ``None`` when no mapping references a source.
        """
        source_crud = WeatherSourceCRUD(self._db)
        for sem in (irr_sem, temp_sem):
            chosen = sem.chosen
            source_id = getattr(chosen, "weather_source_id", None) if chosen else None
            if source_id is not None:
                source = source_crud.get(source_id)
                if source is not None:
                    return source
        return None
