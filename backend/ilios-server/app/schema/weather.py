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
    WeatherProviderAccountStatus,
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


class WeatherSemanticsReconciliationRow(BaseModel):
    """One weather-source-capable device's position in the governed
    weather-semantics taxonomy (WS.4).

    Strictly DISCLOSURE: every field reports what the governance layer already
    recorded. Semantics are NEVER inferred or converted here — when nothing is
    declared the value stays ``unknown`` and the row simply says so.
    """

    device_id: int
    device_name: Optional[str] = None
    device_category: Optional[str] = None
    metric: Optional[str] = None
    mapping_id: Optional[int] = None

    # The single headline state (one of the 9 taxonomy states).
    reconciliation_state: str
    state_label: str
    state_explanation: str
    required_action: Optional[str] = None
    blocking_level: str

    # The declaration-axis state for transparency; this can differ from
    # ``reconciliation_state`` when semantics are undeclared — the headline is then
    # the observed-device state (state 1) or a source-axis state (states 7-9).
    declaration_state: Optional[str] = None
    source_state: str

    declaration_status: Optional[str] = None
    declaration_basis: Optional[str] = None
    needs_re_review: bool = False
    re_review_reason: Optional[str] = None
    expected_model_eligible: bool = False
    physics_usable_irradiance: bool = False
    physics_usable_temperature: bool = False
    irradiance_plane: Optional[str] = None
    temperature_type: Optional[str] = None
    calibration_status: Optional[str] = None
    layer1_message: Optional[str] = None
    eligibility_reason_codes: list[str] = Field(default_factory=list)


class WeatherSemanticsReconciliationResponse(BaseModel):
    """Site-level governed weather-semantics reconciliation rollup (WS.4).

    Strictly READ-ONLY: it performs no writes/commits, never infers or converts
    semantics, never promotes/activates anything, and never touches the
    WeatherResolver, expected formula, ingestion, rollups, the scheduler,
    baselines, ``expected_weather_provenance``, or O&M. It DISCLOSES each
    weather-source-capable device's position in the 9-state taxonomy plus deduped
    site-level counts so a reviewer can see what is declared, what is eligible,
    and what still needs attention.
    """

    site_id: int
    generated_at: datetime
    total_weather_capable_devices: int
    has_weather_source: bool
    has_active_weather_profile: bool
    eligible_count: int
    needs_re_review_count: int
    state_counts: dict[str, int] = Field(default_factory=dict)
    blocking_counts: dict[str, int] = Field(default_factory=dict)
    devices: list[WeatherSemanticsReconciliationRow] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Third-party weather provider framework (Phases A–D) — provider catalog +
# per-company accounts. Additive + CONTEXT-ONLY. The secret VALUE and the
# durable-store ``secret_name`` are NEVER surfaced in any response.
# ---------------------------------------------------------------------------
class WeatherProviderEntry(BaseModel):
    """One registered weather provider (read-only catalog view).

    ``expected_eligible_capable`` is surfaced explicitly and is ALWAYS ``False``
    in Phases A–D: external weather is context-only and never physics-/expected-
    eligible. ``requires_credentials`` is derived from a non-empty config schema
    (keyless providers such as Open-Meteo report ``False``).
    """

    provider_key: str
    display_name: str
    licensing_class: Optional[str] = None
    docs_url: Optional[str] = None
    is_enabled: bool
    requires_credentials: bool
    config_schema: dict[str, Any] = Field(default_factory=dict)
    capabilities: Optional[dict[str, Any]] = None
    expected_eligible_capable: bool = False

    @classmethod
    def from_model(cls, row: Any) -> "WeatherProviderEntry":
        schema = row.config_schema or {}
        return cls(
            provider_key=row.provider_key,
            display_name=row.display_name,
            licensing_class=row.licensing_class,
            docs_url=row.docs_url,
            is_enabled=bool(row.is_enabled),
            requires_credentials=bool(schema),
            config_schema=schema,
            capabilities=row.capabilities_json or None,
            expected_eligible_capable=False,
        )


class WeatherProviderList(BaseModel):
    items: list[WeatherProviderEntry] = Field(default_factory=list)


class WeatherProviderCredentials(BaseModel):
    """Opaque credential field bag for a keyed provider account.

    Values are written ONLY to the durable credential store; they are never
    persisted to the DB, logged, or echoed back in any response.
    """

    fields: dict[str, str] = Field(default_factory=dict)


class WeatherProviderAccountCreate(BaseModel):
    provider_key: str
    display_name: str
    external_account_label: Optional[str] = None
    credentials: Optional[WeatherProviderCredentials] = None
    licensing_acknowledged: bool = False


class WeatherProviderAccountUpdate(BaseModel):
    display_name: Optional[str] = None
    external_account_label: Optional[str] = None
    status: Optional[WeatherProviderAccountStatus] = None
    credentials: Optional[WeatherProviderCredentials] = None
    licensing_acknowledged: Optional[bool] = None


class WeatherProviderAccountResponse(BaseModel):
    """A provider account row.

    The secret value / ``secret_name`` is NEVER included;
    ``credential_fingerprint`` is a non-reversible admin-only hint and
    ``has_stored_credentials`` merely says whether a secret reference exists.
    """

    id: int
    company_id: int
    provider_key: str
    display_name: str
    external_account_label: Optional[str] = None
    status: str
    credential_status: str
    last_sync_status: str
    licensing_acknowledged: bool
    licensing_acknowledged_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    is_archived: bool
    has_stored_credentials: bool
    credential_fingerprint: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @staticmethod
    def _ev(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    @classmethod
    def from_model(
        cls, account: Any, *, credential_fingerprint: Optional[str] = None
    ) -> "WeatherProviderAccountResponse":
        return cls(
            id=account.id,
            company_id=account.company_id,
            provider_key=account.provider_key,
            display_name=account.display_name,
            external_account_label=account.external_account_label,
            status=cls._ev(account.status),
            credential_status=cls._ev(account.credential_status),
            last_sync_status=cls._ev(account.last_sync_status),
            licensing_acknowledged=account.licensing_acknowledged_at is not None,
            licensing_acknowledged_at=account.licensing_acknowledged_at,
            last_success_at=account.last_success_at,
            last_error_at=account.last_error_at,
            last_error_message=account.last_error_message,
            is_archived=bool(account.is_archived),
            has_stored_credentials=bool(account.secret_name),
            credential_fingerprint=credential_fingerprint,
            created_at=getattr(account, "created_at", None),
            updated_at=getattr(account, "updated_at", None),
        )


class WeatherProviderAccountList(BaseModel):
    items: list[WeatherProviderAccountResponse] = Field(default_factory=list)


class WeatherProviderTestResponse(BaseModel):
    success: bool
    message: str
    credential_status: str


# ---------------------------------------------------------------------------
# Third-party provider import (Phase C) — preview / run / batch surfaces.
# CONTEXT-ONLY: a provider pull stores honest measurement semantics (e.g. GHI
# irradiance / ambient temperature) verbatim and converts NOTHING. It never
# marks an external source physics-/expected-eligible, never transposes GHI->POA
# or ambient->cell, and never fabricates a value (a missing reading is the
# ABSENCE of a row). Pulls are gap-only + idempotent (``dedupe_key``) so they
# never re-spend a metered call on a window already stored.
# ---------------------------------------------------------------------------
class ProviderImportRequest(BaseModel):
    """Operator request to pull weather from a registered provider for a window.

    ``account_id`` is required only for keyed providers; keyless providers (e.g.
    Open-Meteo) omit it. ``metrics`` defaults to the provider's full advertised
    metric set. The window is naive-UTC (the existing storage convention) and is
    clamped to the provider's ``max_history_days`` at run time when declared.
    """

    provider_key: str = Field(min_length=1, max_length=64)
    account_id: Optional[int] = None
    window_start: datetime
    window_end: datetime
    metrics: Optional[list[str]] = None
    granularity: str = Field(default="hourly", max_length=16)

    @model_validator(mode="after")
    def _check_window(self) -> "ProviderImportRequest":
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be after window_start")
        return self


class ProviderImportPreviewResponse(BaseModel):
    """Dry-run plan for a provider pull. Writes NOTHING.

    Always reports ``context_only=True`` / ``expected_eligible_capable=False``:
    external weather is context/provenance only and never feeds expected math.
    ``estimated_provider_calls`` reflects gap-fill (windows already stored are
    skipped), so the operator sees the real metered cost before committing.
    """

    provider_key: str
    display_name: str
    licensing_class: Optional[str] = None
    context_only: bool = True
    expected_eligible_capable: bool = False
    verdict: str = "Context-only — not expected-eligible"
    requested_metrics: list[str] = Field(default_factory=list)
    native_plane: str = "unknown"
    native_temperature_type: str = "unknown"
    is_modeled: bool = True
    window_start: datetime
    window_end: datetime
    effective_window_start: Optional[datetime] = None
    effective_window_end: Optional[datetime] = None
    chunk_count: int = 0
    chunks_to_pull: int = 0
    chunks_already_covered: int = 0
    estimated_provider_calls: int = 0
    existing_observation_count: int = 0
    rate_limit_remaining_minute: Optional[int] = None
    rate_limit_remaining_day: Optional[int] = None
    warnings: list[str] = Field(default_factory=list)


class ProviderImportResponse(BaseModel):
    """Outcome of a provider pull (best-effort, partial-tolerant).

    ``status`` mirrors ``pull_status`` (``succeeded`` / ``partial`` / ``failed``).
    A pull that found every window already stored returns ``succeeded`` with
    ``batch_id=None`` and zero writes. ``physics_usable_rows`` is reported for
    transparency and is always 0 for context-only external weather.
    """

    status: str
    pull_status: str
    batch_id: Optional[int] = None
    site_id: int
    weather_source_id: Optional[int] = None
    provider_key: str
    account_id: Optional[int] = None
    context_only: bool = True
    expected_eligible_capable: bool = False
    rows_pulled: int = 0
    rows_inserted: int = 0
    rows_duplicate: int = 0
    distinct_metrics: list[str] = Field(default_factory=list)
    physics_usable_rows: int = 0
    stored_not_usable_rows: int = 0
    modeled_rows: int = 0
    chunks_pulled: int = 0
    chunks_skipped: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    api_version: Optional[str] = None
    rate_limited: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ProviderPullBatchResponse(BaseModel):
    """Read-only view of a ``provider_pull`` provenance batch.

    Exposes only NON-secret provenance: which account, the pull status, the
    window, row count, provider api version, and an error summary (never a
    credential). Request/response hashes stay internal; they are not surfaced.
    """

    id: int
    site_id: int
    weather_source_id: int
    account_id: Optional[int] = None
    batch_kind: str
    pull_status: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    row_count: Optional[int] = None
    provider_api_version: Optional[str] = None
    error_summary: Optional[str] = None
    created_at: Optional[datetime] = None

    @staticmethod
    def _ev(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    @classmethod
    def from_model(cls, batch: Any) -> "ProviderPullBatchResponse":
        return cls(
            id=batch.id,
            site_id=batch.site_id,
            weather_source_id=batch.weather_source_id,
            account_id=getattr(batch, "account_id", None),
            batch_kind=cls._ev(batch.batch_kind),
            pull_status=cls._ev(getattr(batch, "pull_status", None)),
            period_start=batch.period_start,
            period_end=batch.period_end,
            row_count=batch.row_count,
            provider_api_version=getattr(batch, "provider_api_version", None),
            error_summary=getattr(batch, "error_summary", None),
            created_at=getattr(batch, "created_at", None),
        )


class ProviderPullBatchList(BaseModel):
    items: list[ProviderPullBatchResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# External weather CONTEXT (Phase D) — read-only provenance surface.
#
# This response is a pure read aggregation over already-stored external weather.
# It NEVER calls or alters ``compute_weather_readiness`` and never feeds expected
# math: every external source it reports is context-only and structurally
# ``expected_eligible_capable=False`` (carries ghi/ambient/unknown semantics, not
# poa/cell). Absent coverage is the absence of a row — counts are never fabricated.
# ---------------------------------------------------------------------------
class ExternalWeatherContextMetric(BaseModel):
    """Per-metric coverage for one external source (honest, never fabricated)."""

    metric: str
    observation_count: int = 0
    earliest_obs: Optional[datetime] = None
    latest_obs: Optional[datetime] = None


class ExternalWeatherContextSource(BaseModel):
    """One external (modeled) weather source and its stored coverage.

    ``is_modeled`` / ``default_confidence`` are reported verbatim from the source
    row so the UI can label the value honestly ("modeled — <provider>"). The
    source is never represented as physics-/expected-eligible.
    """

    weather_source_id: int
    source_type: str
    provider_key: Optional[str] = None
    display_name: str
    is_modeled: bool = True
    default_confidence: Optional[str] = None
    licensing_note: Optional[str] = None
    active: bool = True
    observation_count: int = 0
    earliest_obs: Optional[datetime] = None
    latest_obs: Optional[datetime] = None
    metrics: list[ExternalWeatherContextMetric] = Field(default_factory=list)


class ExternalWeatherContextResponse(BaseModel):
    """Read-only external-weather context for a site.

    Carries the explicit context-only banner/verdict, the external sources with
    their coverage windows, the most recent provider pull, and recent pull
    provenance. ``expected_eligible_capable`` is always ``False`` — this surface
    exists to make external weather auditable, NOT to feed expected math.
    """

    site_id: int
    context_only: bool = True
    expected_eligible_capable: bool = False
    banner: str = (
        "External weather is context-only and is NOT expected-eligible. "
        "It is never converted to plane-of-array irradiance or cell temperature "
        "and never feeds the expected-production calculation."
    )
    source_count: int = 0
    total_observation_count: int = 0
    sources: list[ExternalWeatherContextSource] = Field(default_factory=list)
    last_pull: Optional[ProviderPullBatchResponse] = None
    recent_batches: list[ProviderPullBatchResponse] = Field(default_factory=list)
