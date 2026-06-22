"""Pydantic schemas for Weather Data Architecture W2 — historical import + readiness.

These schemas are the API surface for the W2 historical weather backfill feature.
They sit on top of the W0 native weather domain (``app/models/weather.py``) and the
W1 :class:`~app.services.weather.weather_resolver.WeatherResolver`. W2 is strictly
additive:

* it never introduces an external provider, secret, BigQuery, or Firestore dependency;
* it never converts GHI/DNI/DHI to plane-of-array (POA) or ambient to cell/module
  temperature — only POA irradiance and cell/module/modeled_cell temperature are
  treated as physics-usable; other measurements are stored verbatim but reported as
  not-usable for the expected calc;
* it never fabricates a value (a missing reading is the ABSENCE of a row);
* it never treats design/PVsyst weather as observed.

The import surface deliberately mirrors the telemetry ingestion contract: imports are
idempotent (re-importing the same window is a no-op via ``dedupe_key``) and
all-or-nothing (a single invalid row rejects the whole import so a batch can never be
half-written).
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.weather import (
    WeatherCalibrationStatus,
    WeatherConfidence,
    WeatherDeclarationBasis,
    WeatherDeclarationStatus,
    WeatherIrradiancePlane,
    WeatherObservationBatchKind,
    WeatherSourceProfileRole,
    WeatherSourceType,
    WeatherTemperatureType,
)

# Irradiance planes that are physics-usable today (no transposition model exists
# in W0/W2): only true plane-of-array. GHI/DNI/DHI are stored verbatim but NEVER
# transposed to POA.
_PHYSICS_USABLE_PLANES = frozenset({WeatherIrradiancePlane.poa})
# Temperature semantics usable by the cell-temperature physics path. Ambient is
# NOT converted to cell/module in W0/W2.
_PHYSICS_USABLE_TEMPERATURES = frozenset(
    {
        WeatherTemperatureType.cell,
        WeatherTemperatureType.module,
        WeatherTemperatureType.modeled_cell,
    }
)


# ---------------------------------------------------------------------------
# Source creation (inline, optional — an import can reference an existing source)
# ---------------------------------------------------------------------------
class WeatherSourceCreate(BaseModel):
    """Inline creation of a :class:`~app.models.weather.WeatherSource`.

    Used when importing historical weather for a site that does not yet have a
    catalogued source. NEVER carries secrets/API keys — only non-secret identity
    and licensing metadata, matching the W0 model invariant.
    """

    display_name: str = Field(min_length=1, max_length=255)
    source_type: WeatherSourceType
    provider_key: Optional[str] = Field(default=None, max_length=128)
    is_modeled: bool = False
    default_confidence: WeatherConfidence = WeatherConfidence.unknown
    licensing_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Import rows + structured errors
# ---------------------------------------------------------------------------
class WeatherImportRow(BaseModel):
    """One historical weather observation to import.

    ``irradiance_plane`` / ``temperature_type`` default to ``unknown`` and are
    NEVER guessed. A row is only physics-usable when the importer explicitly tags
    it as POA irradiance or a cell/module/modeled_cell temperature; everything
    else is stored verbatim but disclosed as not-usable for the expected calc.
    """

    timestamp: datetime
    metric: str = Field(min_length=1, max_length=64)
    value: float
    unit: Optional[str] = Field(default=None, max_length=32)
    irradiance_plane: WeatherIrradiancePlane = WeatherIrradiancePlane.unknown
    temperature_type: WeatherTemperatureType = WeatherTemperatureType.unknown
    is_modeled: bool = False
    confidence: WeatherConfidence = WeatherConfidence.unknown
    source_row_id: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None

    @field_validator("value")
    @classmethod
    def _value_must_be_finite(cls, v: float) -> float:
        # Reject NaN / +-inf at the API boundary; the import service performs the
        # same check so service-level callers (and tests) are equally protected.
        if not math.isfinite(v):
            raise ValueError("value must be a finite number")
        return v


class WeatherImportRowError(BaseModel):
    """A single structured validation error for an import row.

    ``index`` is the 0-based position of the offending row in the submitted list,
    so a client can map the error back to its source file line.
    """

    index: int
    field: str
    message: str
    value: Optional[Any] = None


# ---------------------------------------------------------------------------
# Import preview (dry run — writes nothing)
# ---------------------------------------------------------------------------
class HistoricalImportPreviewRequest(BaseModel):
    """Dry-run validation of import rows. No source is required (nothing is
    written); the preview only validates and summarizes the rows."""

    rows: list[WeatherImportRow] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_rows(self) -> "HistoricalImportPreviewRequest":
        if not self.rows:
            raise ValueError("At least one row is required to preview.")
        return self


class HistoricalImportPreviewResponse(BaseModel):
    """Summary of what an import WOULD do — without writing anything.

    ``physics_usable_rows`` counts rows explicitly tagged as POA irradiance or a
    cell-usable temperature; ``stored_not_usable_rows`` counts valid rows that are
    stored verbatim but cannot drive the physics (e.g. GHI irradiance or ambient
    temperature). The two together never silently convert one into the other.
    """

    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[WeatherImportRowError] = Field(default_factory=list)
    distinct_metrics: list[str] = Field(default_factory=list)
    physics_usable_rows: int = 0
    poa_irradiance_rows: int = 0
    cell_temperature_rows: int = 0
    stored_not_usable_rows: int = 0
    modeled_rows: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Import (writes a batch + idempotent observations, all-or-nothing)
# ---------------------------------------------------------------------------
class HistoricalImportRequest(BaseModel):
    """Import historical weather observations for a site.

    Provide EXACTLY ONE of ``weather_source_id`` (an existing catalogued source)
    or ``source`` (inline create). The import is all-or-nothing: if any row is
    invalid the whole import is rejected and nothing is written.
    """

    weather_source_id: Optional[int] = None
    source: Optional[WeatherSourceCreate] = None
    batch_kind: WeatherObservationBatchKind = WeatherObservationBatchKind.file_import
    unit_system: Optional[str] = Field(default=None, max_length=32)
    timezone_alignment_note: Optional[str] = None
    source_file_id: Optional[int] = None
    rows: list[WeatherImportRow] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> "HistoricalImportRequest":
        if (self.weather_source_id is None) == (self.source is None):
            raise ValueError(
                "Provide exactly one of weather_source_id or source."
            )
        if not self.rows:
            raise ValueError("At least one row is required to import.")
        return self


class HistoricalImportResponse(BaseModel):
    """Outcome of a successful historical import.

    ``rows_inserted`` is the number of NEW observations written; ``rows_duplicate``
    is the number of valid rows that already existed (idempotent re-import), so a
    re-run of the same window reports ``rows_inserted == 0``.
    """

    status: str = "succeeded"
    batch_id: int
    site_id: int
    weather_source_id: int
    rows_received: int
    rows_valid: int
    rows_inserted: int
    rows_duplicate: int
    distinct_metrics: list[str] = Field(default_factory=list)
    physics_usable_rows: int = 0
    stored_not_usable_rows: int = 0
    modeled_rows: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Readiness (coverage of physics-usable historical weather for a window)
# ---------------------------------------------------------------------------
class WeatherGapRange(BaseModel):
    """A contiguous run of expected buckets lacking BOTH usable physics inputs."""

    start: datetime
    end: datetime
    bucket_count: int


class WeatherReadinessResponse(BaseModel):
    """Whether a window has enough physics-usable historical weather to drive an
    honest expected replay, with an auditable breakdown of the gaps.

    Counts are over the epoch-anchored expected buckets for the window (the same
    bucket grid the rollups use), so coverage percentages are honest denominators
    rather than guesses. A bucket is "usable" only when it holds a POA irradiance
    or cell-usable temperature observation; unknown/ambient/GHI observations are
    counted under ``unknown_semantics_buckets`` and never promoted.
    """

    site_id: int
    window_start: datetime
    window_end: datetime
    bucket_size: str
    role: str
    has_active_historical_profile: bool = False
    profile_id: Optional[int] = None
    profile_partial_window: bool = False
    total_expected_buckets: int = 0
    irradiance_usable_buckets: int = 0
    cell_temperature_usable_buckets: int = 0
    both_usable_buckets: int = 0
    missing_irradiance_buckets: int = 0
    missing_cell_temperature_buckets: int = 0
    unknown_semantics_buckets: int = 0
    coverage_pct: float = 0.0
    irradiance_coverage_pct: float = 0.0
    cell_temperature_coverage_pct: float = 0.0
    modeled_usable_buckets: int = 0
    confidence_summary: dict[str, int] = Field(default_factory=dict)
    gap_ranges: list[WeatherGapRange] = Field(default_factory=list)
    ready_for_expected_replay: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    indicators: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Profile creation + approval lifecycle
# ---------------------------------------------------------------------------
class HistoricalProfileCreateRequest(BaseModel):
    """Create a (draft) weather source profile for a site.

    Profiles are versioned by NEW ROW and never auto-activated — a created profile
    always starts ``draft`` and only an explicit approval action makes it active.
    """

    weather_source_id: int
    role: WeatherSourceProfileRole = WeatherSourceProfileRole.historical
    priority: int = 0
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    fallback_allowed: bool = False
    external_modeled_allowed: bool = False
    min_confidence_policy: Optional[WeatherConfidence] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate_window(self) -> "HistoricalProfileCreateRequest":
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to <= self.effective_from
        ):
            raise ValueError("effective_to must be after effective_from.")
        return self


class WeatherProfileResponse(BaseModel):
    """A weather source profile row (enum fields surfaced as their string values)."""

    id: int
    site_id: int
    role: str
    weather_source_id: int
    priority: int
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    fallback_allowed: bool
    external_modeled_allowed: bool
    min_confidence_policy: Optional[str] = None
    status: str
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    notes: Optional[str] = None

    @staticmethod
    def _ev(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    @classmethod
    def from_model(cls, profile: Any) -> "WeatherProfileResponse":
        return cls(
            id=profile.id,
            site_id=profile.site_id,
            role=cls._ev(profile.role),
            weather_source_id=profile.weather_source_id,
            priority=profile.priority,
            effective_from=profile.effective_from,
            effective_to=profile.effective_to,
            fallback_allowed=profile.fallback_allowed,
            external_modeled_allowed=profile.external_modeled_allowed,
            min_confidence_policy=cls._ev(profile.min_confidence_policy),
            status=cls._ev(profile.status),
            approved_by=profile.approved_by,
            approved_at=profile.approved_at,
            notes=profile.notes,
        )


class WeatherProfileActionRequest(BaseModel):
    """Apply an approval-lifecycle action to a profile.

    ``approve`` transitions the profile to ``active`` (so the existing resolver
    profile selection picks it up); ``reject`` to ``rejected``; ``revoke`` /
    ``supersede`` to ``superseded``. Every action appends an immutable
    approval-ledger entry and only touches the lifecycle fields, never policy.
    """

    action: str
    rationale: Optional[str] = None


class WeatherProfileActionResponse(BaseModel):
    """Result of an approval action: the updated profile + the ledger entry id."""

    profile: WeatherProfileResponse
    approval_id: int
    action: str
    status: str


# ---------------------------------------------------------------------------
# Weather device semantics (declare what a device's weather stream MEANS)
# ---------------------------------------------------------------------------
class WeatherDeviceMappingDeclareRequest(BaseModel):
    """Declare measurement semantics for a weather-source device stream.

    Semantics are NEVER guessed: ``irradiance_plane`` / ``temperature_type`` /
    ``calibration_status`` all default to ``unknown`` and only an explicit operator
    declaration sets POA / cell / etc. W0/W2 performs NO conversion — declaring GHI
    does not transpose it to POA, and declaring ambient does not promote it to cell.
    Each declaration is appended as a NEW effective-dated row; history is never
    rewritten.
    """

    device_id: int
    metric: str = Field(min_length=1, max_length=64)
    # WS.2 governance: every governed declaration MUST rest on a declared basis;
    # the basis decides whether it can ever become ``expected_model_eligible``.
    declaration_basis: WeatherDeclarationBasis
    weather_source_id: Optional[int] = None
    external_device_id: Optional[str] = Field(default=None, max_length=255)
    provider_key: Optional[str] = Field(default=None, max_length=128)
    irradiance_plane: WeatherIrradiancePlane = WeatherIrradiancePlane.unknown
    temperature_type: WeatherTemperatureType = WeatherTemperatureType.unknown
    calibration_status: WeatherCalibrationStatus = WeatherCalibrationStatus.unknown
    calibrated_at: Optional[datetime] = None
    calibration_reference: Optional[str] = Field(default=None, max_length=255)
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    # WS.2 evidence + audit fields (cross-tenant resolvability validated in the
    # service; shapes per declaration basis enforced server-side, never inferred).
    source_document_id: Optional[int] = None
    source_file_id: Optional[int] = None
    reviewer_note: Optional[str] = None
    sensor_role: Optional[str] = Field(default=None, max_length=128)
    sensor_model: Optional[str] = Field(default=None, max_length=255)
    provider_metadata_json: Optional[dict[str, Any]] = None
    # Optional explicit supersession target (must share site/device/metric); the
    # prior active row is only flipped to ``superseded`` on successful activation.
    supersedes_mapping_id: Optional[int] = None
    # ``reviewer_assumption`` basis requires an explicit operator confirmation so a
    # bare assumption can never be declared without friction.
    assumption_confirmed: bool = False
    # When true the draft is created AND activated atomically (create + activate).
    activate: bool = False

    @model_validator(mode="after")
    def _validate_window(self) -> "WeatherDeviceMappingDeclareRequest":
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to <= self.effective_from
        ):
            raise ValueError("effective_to must be after effective_from.")
        return self


class WeatherDeclarationActivateRequest(BaseModel):
    """Activate an existing draft declaration (full governance validation).

    Activation never *infers* anything: it validates the stored basis/evidence is
    complete and in-tenant, and — if the draft carries a ``supersedes_mapping_id``
    — atomically flips the prior active row to ``superseded`` in the same
    transaction. An optional rationale is recorded on the ledger event.
    """

    rationale: Optional[str] = None


class WeatherDeclarationReReviewRequest(BaseModel):
    """Manually flag an active declaration as needing re-review (monotonic flag).

    ``needs_re_review`` is a boolean flag (NOT a status); it is set false->true
    only and is NEVER auto-cleared — it clears only when a new activated
    declaration supersedes the stale row.
    """

    reason: str = Field(min_length=1)


class WeatherDeviceMappingResponse(BaseModel):
    """A declared weather device mapping (enum fields surfaced as string values).

    ``physics_usable_irradiance`` / ``physics_usable_temperature`` are additive,
    read-only disclosures of whether the declared semantics are usable by the
    expected physics today (POA / cell-usable). They DISCLOSE; they never convert
    or upgrade an ``unknown``/GHI/ambient declaration.
    """

    id: int
    site_id: int
    device_id: Optional[int] = None
    external_device_id: Optional[str] = None
    weather_source_id: Optional[int] = None
    metric: str
    provider_key: Optional[str] = None
    irradiance_plane: str
    temperature_type: str
    calibration_status: str
    calibrated_at: Optional[datetime] = None
    calibration_reference: Optional[str] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    physics_usable_irradiance: bool = False
    physics_usable_temperature: bool = False
    # -- WS.2 governance (additive; NULL on legacy/ungoverned rows) ----------
    declaration_status: Optional[str] = None
    declaration_basis: Optional[str] = None
    declared_by: Optional[int] = None
    declared_at: Optional[datetime] = None
    activated_by: Optional[int] = None
    activated_at: Optional[datetime] = None
    supersedes_mapping_id: Optional[int] = None
    superseded_by_mapping_id: Optional[int] = None
    needs_re_review: bool = False
    re_review_reason: Optional[str] = None
    source_document_id: Optional[int] = None
    source_file_id: Optional[int] = None
    reviewer_note: Optional[str] = None
    sensor_role: Optional[str] = None
    sensor_model: Optional[str] = None
    # -- WS.2 derived verdict (read-only; never persisted, never converts) ---
    expected_model_eligible: bool = False
    declaration_state: Optional[str] = None
    eligibility_reason_codes: list[str] = Field(default_factory=list)
    eligibility_blocking_level: Optional[str] = None
    eligibility_required_action: Optional[str] = None
    layer1_message: Optional[str] = None

    @staticmethod
    def _ev(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    @classmethod
    def from_model(cls, mapping: Any) -> "WeatherDeviceMappingResponse":
        # Lazy import avoids a schema<->policy import cycle (the pure policy
        # module imports the physics-usable sets from this schema module).
        from app.services.weather.declaration_policy import evaluate_mapping

        verdict = evaluate_mapping(mapping)
        return cls(
            id=mapping.id,
            site_id=mapping.site_id,
            device_id=mapping.device_id,
            external_device_id=mapping.external_device_id,
            weather_source_id=mapping.weather_source_id,
            metric=mapping.metric,
            provider_key=mapping.provider_key,
            irradiance_plane=cls._ev(mapping.irradiance_plane),
            temperature_type=cls._ev(mapping.temperature_type),
            calibration_status=cls._ev(mapping.calibration_status),
            calibrated_at=mapping.calibrated_at,
            calibration_reference=mapping.calibration_reference,
            effective_from=mapping.effective_from,
            effective_to=mapping.effective_to,
            physics_usable_irradiance=verdict.physics_usable_irradiance,
            physics_usable_temperature=verdict.physics_usable_temperature,
            declaration_status=cls._ev(getattr(mapping, "declaration_status", None)),
            declaration_basis=cls._ev(getattr(mapping, "declaration_basis", None)),
            declared_by=getattr(mapping, "declared_by", None),
            declared_at=getattr(mapping, "declared_at", None),
            activated_by=getattr(mapping, "activated_by", None),
            activated_at=getattr(mapping, "activated_at", None),
            supersedes_mapping_id=getattr(mapping, "supersedes_mapping_id", None),
            superseded_by_mapping_id=getattr(mapping, "superseded_by_mapping_id", None),
            needs_re_review=bool(getattr(mapping, "needs_re_review", None)),
            re_review_reason=getattr(mapping, "re_review_reason", None),
            source_document_id=getattr(mapping, "source_document_id", None),
            source_file_id=getattr(mapping, "source_file_id", None),
            reviewer_note=getattr(mapping, "reviewer_note", None),
            sensor_role=getattr(mapping, "sensor_role", None),
            sensor_model=getattr(mapping, "sensor_model", None),
            expected_model_eligible=verdict.expected_model_eligible,
            declaration_state=verdict.declaration_state,
            eligibility_reason_codes=list(verdict.reason_codes),
            eligibility_blocking_level=verdict.blocking_level,
            eligibility_required_action=verdict.required_action,
            layer1_message=verdict.layer1_message,
        )


class WeatherUpstreamMappingDivergence(BaseModel):
    """Per-declaration upstream-divergence row (WS.3, read-only description).

    A verbatim projection of the detector's ``MappingDivergence`` dataclass. It
    describes whether an ACTIVE declaration's device upstream identity has drifted
    from the fingerprint snapshot taken at declaration time. It carries NO
    semantics value and never implies a conversion.
    """

    model_config = ConfigDict(from_attributes=True)

    mapping_id: int
    device_id: Optional[int] = None
    metric: Optional[str] = None
    needs_re_review: bool
    has_stored_fingerprint: bool
    diverged: bool
    changed_keys: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    would_flag: bool
    flagged: bool = False

    @classmethod
    def from_dc(cls, dc: Any) -> "WeatherUpstreamMappingDivergence":
        return cls(
            mapping_id=dc.mapping_id,
            device_id=dc.device_id,
            metric=dc.metric,
            needs_re_review=dc.needs_re_review,
            has_stored_fingerprint=dc.has_stored_fingerprint,
            diverged=dc.diverged,
            changed_keys=list(dc.changed_keys),
            summary=dc.summary,
            would_flag=dc.would_flag,
            flagged=dc.flagged,
        )


class WeatherUpstreamReEvaluateResponse(BaseModel):
    """Site-level upstream re-evaluation rollup (WS.3).

    ``applied=False`` is the read-only preview (no writes occurred);
    ``applied=True`` is returned by the admin re-evaluate action after monotonic
    ``needs_re_review`` flags were raised on diverged, not-already-flagged rows.
    """

    site_id: int
    applied: bool
    total_active: int
    diverged_count: int
    would_flag_count: int
    already_flagged_count: int
    newly_flagged_count: int
    mappings: list[WeatherUpstreamMappingDivergence] = Field(default_factory=list)

    @classmethod
    def from_report(cls, report: Any) -> "WeatherUpstreamReEvaluateResponse":
        return cls(
            site_id=report.site_id,
            applied=report.applied,
            total_active=report.total_active,
            diverged_count=report.diverged_count,
            would_flag_count=report.would_flag_count,
            already_flagged_count=report.already_flagged_count,
            newly_flagged_count=report.newly_flagged_count,
            mappings=[
                WeatherUpstreamMappingDivergence.from_dc(m) for m in report.mappings
            ],
        )
