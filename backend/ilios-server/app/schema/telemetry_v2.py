"""Pydantic schemas for the v2 telemetry API.

Credential fields are write-only — they are accepted on create/update payloads
but never appear on response schemas. The three-state account model
(``status``, ``credential_status``, ``last_sync_status``) is exposed on
account responses without ever leaking credential values.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.telemetry import (
    CompanyProviderStatus,
    CredentialStatus,
    ExternalSiteSyncStatus,
    LastSyncStatus,
    ProviderAccountStatus,
    TelemetrySyncScope,
    TelemetrySyncStatus,
    TelemetrySyncTrigger,
)
from app.models.telemetry_expected import (
    TelemetryBaselineSource,
    TelemetryBaselineStatus,
    TelemetryBaselineType,
)
from app.schema.weather import WeatherSemanticsReconciliationResponse


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


class ProviderCatalogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_key: str = Field(examples=["also_energy"])
    display_name: str = Field(examples=["Also Energy"])
    config_schema: dict[str, Any] = Field(default_factory=dict)
    docs_url: Optional[str] = None
    is_enabled: bool = True


class ProviderCatalogList(BaseModel):
    items: list[ProviderCatalogEntry]


# ---------------------------------------------------------------------------
# Company licenses
# ---------------------------------------------------------------------------


class LicensedProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    provider_key: str = Field(description="Catalog key (e.g. 'also_energy')")
    display_name: str = Field(description="Human-friendly provider name")
    status: CompanyProviderStatus = CompanyProviderStatus.active
    notes: Optional[str] = None
    account_count: int = Field(default=0, description="Number of provider accounts using this license")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LicensedProviderList(BaseModel):
    items: list[LicensedProviderResponse]


class LicenseCreateRequest(BaseModel):
    provider_key: str = Field(description="Provider catalog key", examples=["also_energy"])
    notes: Optional[str] = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Provider accounts (formerly DAS connections)
# ---------------------------------------------------------------------------


class ProviderAccountCredentials(BaseModel):
    """Write-only credential payload validated against the catalog config schema."""

    fields: dict[str, str] = Field(
        default_factory=dict,
        description="Provider-specific credential fields (e.g. token, username/password).",
    )

    @field_validator("fields")
    @classmethod
    def _strip_blank(cls, v: dict[str, str]) -> dict[str, str]:
        return {k: val for k, val in v.items() if val is not None and val != ""}


class ProviderAccountCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    provider_key: str = Field(description="Provider catalog key", examples=["also_energy"])
    external_account_label: Optional[str] = Field(default=None, max_length=255)
    credentials: ProviderAccountCredentials = Field(
        description="Write-only credential payload"
    )

    @model_validator(mode="after")
    def _require_credentials(self):
        if not self.credentials.fields:
            raise ValueError("credentials.fields is required and cannot be empty")
        return self


class ProviderAccountUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    external_account_label: Optional[str] = Field(default=None, max_length=255)
    status: Optional[ProviderAccountStatus] = None
    credentials: Optional[ProviderAccountCredentials] = Field(
        default=None,
        description="Optional rotation; omit to leave credentials unchanged",
    )


class ProviderAccountResponse(BaseModel):
    """Response — never includes credentials in any form."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    provider_key: str
    display_name: str
    external_account_label: Optional[str] = None
    status: ProviderAccountStatus
    credential_status: CredentialStatus
    last_sync_status: LastSyncStatus
    last_success_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    credentials_fingerprint: Optional[str] = Field(
        default=None,
        description="Short non-reversible fingerprint of stored credentials, "
        "for operator correlation only.",
    )
    external_site_count: int = Field(
        default=0,
        description=(
            "Number of external sites currently known for this provider "
            "account. Counted server-side and tenant-scoped; defaults to 0 "
            "if the count cannot be computed."
        ),
    )
    active_mapping_count: int = Field(
        default=0,
        description=(
            "Number of active project/site mappings for this provider "
            "account. Archived/inactive mappings are excluded. Counted "
            "server-side and tenant-scoped; defaults to 0 if the count "
            "cannot be computed."
        ),
    )


class ProviderAccountList(BaseModel):
    items: list[ProviderAccountResponse]


class TestAccountResponse(BaseModel):
    success: bool
    message: str
    credential_status: CredentialStatus
    available_sites_count: Optional[int] = None


# ---------------------------------------------------------------------------
# External sites (sync provenance)
# ---------------------------------------------------------------------------


class ExternalSiteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_account_id: int
    external_site_id: str
    external_site_name: Optional[str] = None
    sync_status: ExternalSiteSyncStatus
    first_seen_at: datetime
    last_seen_at: datetime
    last_synced_at: datetime
    last_sync_run_id: Optional[str] = None
    last_sync_error: Optional[str] = None


class ExternalSiteList(BaseModel):
    items: list[ExternalSiteResponse]
    last_sync_run_id: Optional[str] = None
    last_sync_status: LastSyncStatus
    last_success_at: Optional[datetime] = None


class SyncSitesResponse(BaseModel):
    sync_run_id: str
    last_sync_status: LastSyncStatus
    seen_count: int
    new_count: int
    missing_count: int
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Site mappings (richer m:n)
# ---------------------------------------------------------------------------


class SiteMappingCreateRequest(BaseModel):
    """Body for the V2 (DB-only) project/site mapping save.

    The mapping is keyed on ``{provider_account_id, external_site_id}``; the
    display name is resolved server-side from the iliOS external-site cache, so
    no live provider call is needed when the site has already been synced.
    """

    provider_account_id: int
    external_site_id: str = Field(min_length=1, max_length=255)
    mapping_role: str = Field(default="primary", max_length=32)


class SiteMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: Optional[int]
    company_id: Optional[int] = None
    connection_id: Optional[int] = None
    provider_account_id: Optional[int]
    telemetry_site_id: str
    telemetry_site_name: str
    mapping_role: str = "primary"
    is_active: bool = True
    created_by_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SiteMappingList(BaseModel):
    items: list[SiteMappingResponse]


# ---------------------------------------------------------------------------
# External devices (per-site hardware sync cache)
# ---------------------------------------------------------------------------


class ExternalDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider_account_id: int
    external_site_id: str
    external_device_id: str
    external_device_name: Optional[str] = None
    sync_status: ExternalSiteSyncStatus
    first_seen_at: datetime
    last_seen_at: datetime
    last_synced_at: datetime
    last_sync_run_id: Optional[str] = None
    last_sync_error: Optional[str] = None


class ExternalDeviceList(BaseModel):
    items: list[ExternalDeviceResponse]
    last_sync_run_id: Optional[str] = None
    last_sync_status: LastSyncStatus
    last_success_at: Optional[datetime] = None


class SyncDevicesResponse(BaseModel):
    sync_run_id: str
    last_sync_status: LastSyncStatus
    seen_count: int
    new_count: int
    missing_count: int
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Device mappings (project device <-> external device) -- DB-only
# ---------------------------------------------------------------------------


class DeviceMappingItem(BaseModel):
    """A single iliOS device -> external device pairing.

    ``device_id`` is the iliOS ``Device`` primary key; ``external_device_id`` is
    the provider's device identifier. The display name is resolved server-side
    from the synced device cache, so it is not accepted here.
    """

    device_id: int
    external_device_id: str = Field(min_length=1, max_length=255)
    device_role: str = Field(default="primary", max_length=32)


class DeviceMappingBulkRequest(BaseModel):
    """Body for the V2 (DB-only) bulk device mapping save.

    Mappings are keyed on ``{provider_account_id, external_site_id}``; each
    external device must already exist in the iliOS device sync cache so no live
    provider call is needed to save.
    """

    provider_account_id: int
    external_site_id: str = Field(min_length=1, max_length=255)
    mappings: list[DeviceMappingItem] = Field(default_factory=list)


class DeviceMappingBulkResponse(BaseModel):
    successful_count: int
    failed_count: int
    errors: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Native readings ingestion — manual refresh
# ---------------------------------------------------------------------------


class RefreshReadingsRequest(BaseModel):
    """Body for the manual single-site readings refresh.

    Both bounds are optional: omitting them refreshes the most recent 24h. The
    endpoint clamps any supplied window to a maximum span (and rejects an
    inverted window) so a manual refresh can never trigger an unbounded pull.
    Timestamps are interpreted as UTC.
    """

    window_start: Optional[datetime] = Field(
        default=None, description="UTC start of the pull window (inclusive)."
    )
    window_end: Optional[datetime] = Field(
        default=None, description="UTC end of the pull window (inclusive)."
    )


class RefreshReadingsResponse(BaseModel):
    """Structured outcome of a manual readings refresh.

    Always returned (even for provider failures) so the UI can show a
    "last refreshed" time and an accurate status without inspecting raw rows.
    """

    sync_job_id: int
    correlation_id: str
    status: TelemetrySyncStatus
    site_id: int
    company_id: int
    provider_key: Optional[str] = None
    external_site_id: Optional[str] = None
    window_start: datetime
    window_end: datetime
    devices_mapped: int = 0
    devices_seen: int = 0
    targets_attempted: int = 0
    targets_with_data: int = 0
    targets_failed: int = 0
    targets_ambiguous: int = 0
    readings_received: int = 0
    readings_written: int = 0
    rate_limited: bool = False
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error: Optional[str] = None
    errors: list[str] = Field(default_factory=list)
    cooldown_seconds: int = Field(
        default=0,
        description=(
            "Seconds until another manual refresh/backfill is allowed for this "
            "project (shared per-project cooldown). 0 means available now."
        ),
    )


class SchedulerStateResponse(BaseModel):
    """Current automation state for one mapped site's telemetry scheduler.

    Returned even when no scheduler row exists yet (synthesized defaults:
    ``enabled=False``, default cadence) so the UI can render a consistent
    control without a separate "configured?" probe.
    """

    site_id: int
    provider_account_id: Optional[int] = None
    company_id: Optional[int] = None
    enabled: bool = False
    cadence: str = "PT1H"
    next_due_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    last_successful_pull_at: Optional[datetime] = None
    last_sync_job_id: Optional[int] = None
    locked_until: Optional[datetime] = None


class SchedulerUpdateRequest(BaseModel):
    """Enable/disable or change cadence for one site's scheduler.

    Both fields are optional so a caller can change just one. ``cadence`` is
    validated server-side against the cadence whitelist; an unknown value is
    rejected with 422.
    """

    enabled: Optional[bool] = Field(
        default=None, description="Enable or disable scheduled ingestion."
    )
    cadence: Optional[str] = Field(
        default=None,
        description="ISO-8601 cadence (e.g. PT1H). Must be a whitelisted value.",
    )


class CompanySchedulerStatusList(BaseModel):
    """Per-site scheduler status across a company's mapped telemetry sites."""

    company_id: int
    items: list[SchedulerStateResponse] = Field(default_factory=list)


class BackfillReadingsRequest(BaseModel):
    """Body for a bounded historical backfill of native readings.

    Provide either a ``preset`` (``7d`` / ``30d``) or an explicit window. The
    total span is capped at 30 days; an inverted or oversized window is rejected
    with 422. Timestamps are interpreted as UTC.
    """

    preset: Optional[str] = Field(
        default=None, description="Convenience window: '7d' or '30d'."
    )
    window_start: Optional[datetime] = Field(
        default=None, description="UTC start of the backfill window (inclusive)."
    )
    window_end: Optional[datetime] = Field(
        default=None,
        description="UTC end of the backfill window (inclusive); defaults to now.",
    )


class BackfillChunkResult(BaseModel):
    """Outcome of one 24h backfill chunk."""

    window_start: datetime
    window_end: datetime
    sync_job_id: Optional[int] = None
    status: str
    readings_received: int = 0
    readings_written: int = 0
    rollup_status: Optional[str] = None
    error: Optional[str] = None


class BackfillReadingsResponse(BaseModel):
    """Aggregate outcome of a bounded backfill.

    ``status`` is succeeded | partial | failed. The backfill processes 24h
    chunks oldest->newest and stops on the first failed chunk, returning every
    chunk attempted. It NEVER advances the scheduled cursor.
    """

    site_id: int
    company_id: Optional[int] = None
    status: str
    requested_window_start: datetime
    requested_window_end: datetime
    chunks_total: int = 0
    chunks_succeeded: int = 0
    chunks_failed: int = 0
    readings_received: int = 0
    readings_written: int = 0
    chunks: list[BackfillChunkResult] = Field(default_factory=list)
    error: Optional[str] = None
    cooldown_seconds: int = Field(
        default=0,
        description=(
            "Seconds until another manual refresh/backfill is allowed for this "
            "project (shared per-project cooldown). 0 means available now."
        ),
    )


# ---------------------------------------------------------------------------
# Read-only rollup views (chart wiring)
#
# These power the V2 telemetry read API and the O&M chart precedence (V2 ->
# BigQuery -> empty). They are derived purely from the PostgreSQL rollup/reading
# tables; building them never calls a provider, touches credentials, or reads
# BigQuery. Every list defaults to empty so an unmapped/empty site returns a
# successful empty payload rather than an error.
# ---------------------------------------------------------------------------


class TelemetrySeriesPoint(BaseModel):
    """One rollup bucket of a normalized metric."""

    bucket_start: datetime
    value: float
    sample_count: int = 0
    completeness: Optional[float] = None


class TelemetrySeriesResponse(BaseModel):
    """Site-level rollup series for one metric + bucket size."""

    site_id: int
    metric: str
    bucket_size: str
    unit: Optional[str] = None
    agg: Optional[str] = None
    count: int = 0
    latest_bucket_start: Optional[datetime] = None
    points: list[TelemetrySeriesPoint] = Field(default_factory=list)


class TelemetryDeviceSeries(BaseModel):
    """One device's rollup series for the requested metric."""

    device_id: int
    device_name: Optional[str] = None
    unit: Optional[str] = None
    count: int = 0
    points: list[TelemetrySeriesPoint] = Field(default_factory=list)


class TelemetryDeviceSeriesResponse(BaseModel):
    """Per-device rollup series for one metric + bucket size."""

    site_id: int
    metric: str
    bucket_size: str
    devices: list[TelemetryDeviceSeries] = Field(default_factory=list)


class TelemetryLatestMetric(BaseModel):
    """Latest known value of a normalized metric for a site."""

    metric: str
    value: float
    unit: Optional[str] = None
    bucket_size: Optional[str] = None
    bucket_start: datetime


class TelemetryLatestResponse(BaseModel):
    """Freshness snapshot: newest reading/rollup time + latest per-metric values."""

    site_id: int
    latest_reading_at: Optional[datetime] = None
    latest_bucket_start: Optional[datetime] = None
    metrics: list[TelemetryLatestMetric] = Field(default_factory=list)


class TelemetrySyncJobSummary(BaseModel):
    """A single ingestion attempt, for surfacing last-sync status."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    scope: TelemetrySyncScope
    status: TelemetrySyncStatus
    trigger: TelemetrySyncTrigger
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    records_received: int = 0
    records_written: int = 0
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class TelemetrySyncJobListResponse(BaseModel):
    """Most-recent-first ingestion attempts for a site."""

    site_id: int
    jobs: list[TelemetrySyncJobSummary] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Performance context aggregator (read-only, composition-only)
#
# A single canonical envelope that COMPOSES already-computed V2 reads — the
# period-effective expected calc, native rollup actuals, governed weather
# semantics reconciliation, and eligibility diagnostics — without re-deriving
# any formula, governance verdict, or eligibility decision. Nullable-everywhere:
# null means "unavailable" and 0 means "a genuine measured zero"; a negative
# tare is preserved verbatim and an expected/variance is never fabricated.
# ---------------------------------------------------------------------------


class PerformanceContextProvenance(BaseModel):
    """Per-bucket provenance: which metrics/baseline produced the values."""

    actual_metric: Optional[str] = None
    actual_unit: Optional[str] = None
    actual_agg: Optional[str] = None
    expected_baseline_id: Optional[int] = None
    baseline_selection_mode: Optional[str] = None
    irradiance_metric: Optional[str] = None
    irradiance_source_id: Optional[int] = None
    temperature_metric: Optional[str] = None
    temperature_source_id: Optional[int] = None
    # The governed weather_device_mapping (if any) backing the weather labels for
    # this bucket; null when no governed mapping produced the value (never faked).
    weather_declaration_mapping_id: Optional[int] = None


class PerformanceContextPoint(BaseModel):
    """One time bucket of composed actual / expected / weather context.

    Every numeric field is nullable: ``null`` == unavailable, ``0`` == a genuine
    measured zero (a negative tare is preserved), and an expected/variance is
    never fabricated when an input is missing.
    """

    bucket_start: datetime
    bucket_start_utc: datetime
    bucket_start_site_local: Optional[datetime] = None

    actual_kw: Optional[float] = None
    actual_kwh: Optional[float] = None
    actual_state: str

    expected_kw: Optional[float] = None
    expected_kwh: Optional[float] = None
    expected_state: str
    baseline_id: Optional[int] = None

    variance_kwh: Optional[float] = None
    variance_pct: Optional[float] = None

    irradiance_wm2: Optional[float] = None
    temperature: Optional[float] = None

    sample_count: Optional[int] = None
    completeness: Optional[float] = None

    source_provenance: PerformanceContextProvenance = Field(
        default_factory=PerformanceContextProvenance
    )


class PerformanceContextWeatherMetric(BaseModel):
    """Compact, verbatim per-metric weather semantics summary.

    Every field is copied verbatim from the governed semantics reconciliation
    rows — no label is invented and no state is recomputed.
    """

    label: Optional[str] = None
    plane: Optional[str] = None
    type: Optional[str] = None
    basis: Optional[str] = None
    expected_model_eligible: bool = False
    used_by_active_model: bool = False


class PerformanceContextWeatherSemantics(BaseModel):
    """Governed weather semantics, projected verbatim (never re-derived).

    The compact ``irradiance``/``temperature`` blocks and the ``headline_state`` /
    ``blocking_level`` are selected from the reconciliation rows; the full
    reconciliation response is embedded under ``reconciliation`` so a consumer can
    read the authoritative rows directly.
    """

    irradiance: PerformanceContextWeatherMetric = Field(
        default_factory=PerformanceContextWeatherMetric
    )
    temperature: PerformanceContextWeatherMetric = Field(
        default_factory=PerformanceContextWeatherMetric
    )
    headline_state: Optional[str] = None
    blocking_level: Optional[str] = None
    reconciliation: Optional["WeatherSemanticsReconciliationResponse"] = None


class PerformanceContextBaselineStatus(BaseModel):
    """The active baseline's read-time health for the window (never mutated)."""

    expected_baseline_available: bool = False
    expected_state: str
    baseline_id: Optional[int] = None
    baseline_type: Optional[str] = None
    baseline_selection_mode: Optional[str] = None
    # Additive fail-closed metadata, non-null only when the active baseline is
    # physically invalid (validated on read).
    baseline_invalid: Optional[bool] = None
    invalid_baseline_id: Optional[int] = None
    baseline_validation_summary: Optional[Any] = None
    baseline_validation_policy_version: Optional[str] = None
    required_action: Optional[str] = None


class PerformanceContextTelemetryQuality(BaseModel):
    """Eligibility/mapping counts (verbatim) + native-read freshness."""

    total_devices: int = 0
    mappable_count: int = 0
    mapped_count: int = 0
    unmapped_eligible_count: int = 0
    expected_driving_count: int = 0
    weather_source_count: int = 0
    weather_unknown_semantics_count: int = 0

    latest_reading_at: Optional[datetime] = None
    latest_bucket_start: Optional[datetime] = None
    data_delay_minutes: Optional[int] = None
    freshness_state: str = "no_data"


class PerformanceContextSummary(BaseModel):
    """Window-level rollup of the composed series (honest, never fabricated)."""

    window_start: datetime
    window_end: datetime
    bucket_size: str
    temp_unit: str
    bucket_count: int = 0

    total_actual_kwh: Optional[float] = None
    total_expected_kwh: Optional[float] = None
    variance_kwh: Optional[float] = None
    variance_pct: Optional[float] = None

    actual_state: str
    expected_state: str


class PerformanceContextWindow(BaseModel):
    """The resolved bounded window as naive-UTC instants plus a tz disclosure note.

    ``start``/``end`` are the canonical naive-UTC bounds (the query/storage axis);
    ``tz_note`` states verbatim that ``site_timezone`` shifts ONLY the day/'today'
    boundary, never the stored timestamps.
    """

    start: datetime
    end: datetime
    tz_note: str = (
        "all timestamps are naive-UTC; site_timezone affects only "
        "day/'today' boundaries"
    )


class PerformanceContextResponse(BaseModel):
    """Canonical read-only V2 performance-context envelope (composition-only)."""

    site_id: int
    # IANA tz (e.g. "America/New_York"); affects ONLY the 'today'/daily boundary,
    # never how timestamps render. Falls back to "UTC" when the site has none.
    site_timezone: Optional[str] = None
    window: PerformanceContextWindow
    # Flat bounds retained additively for back-compat with earlier callers; the
    # canonical bounds are ``window.start``/``window.end``.
    window_start: datetime
    window_end: datetime
    bucket_size: str
    temp_unit: str

    series: list[PerformanceContextPoint] = Field(default_factory=list)
    weather_semantics: PerformanceContextWeatherSemantics = Field(
        default_factory=PerformanceContextWeatherSemantics
    )
    baseline_status: PerformanceContextBaselineStatus
    telemetry_quality: PerformanceContextTelemetryQuality = Field(
        default_factory=PerformanceContextTelemetryQuality
    )
    summary: PerformanceContextSummary


# ---------------------------------------------------------------------------
# Expected-performance baselines (P3.1 / P3.2)
# ---------------------------------------------------------------------------


class ExpectedBaselineCreateRequest(BaseModel):
    """Create a draft expected baseline.

    Physics parameters are NOT in the V2 schema (they lived in the legacy
    BigQuery characteristics tables), so they are supplied here and snapshot onto
    the immutable baseline. Loss %, PTO date and timezone are optional — when
    omitted they are snapshot from the site (losses abs()-normalized).

    Percent-valued fields are PERCENT (e.g. ``98.5`` for 98.5 %).
    """

    model_config = ConfigDict(protected_namespaces=())

    baseline_name: str = Field(min_length=1, max_length=255)
    baseline_type: TelemetryBaselineType = TelemetryBaselineType.weather_adjusted_model
    source_type: Optional[TelemetryBaselineSource] = None
    source_document_id: Optional[int] = None
    source_project_fact_id: Optional[int] = None

    timezone: Optional[str] = Field(default=None, max_length=64)
    system_size_ac_kw: Optional[float] = None
    system_size_dc_kw: Optional[float] = None
    degradation_rate: Optional[float] = None

    module_wattage: Optional[float] = None
    module_quantity: Optional[float] = None
    inverter_wattage: Optional[float] = None
    inverter_quantity: Optional[float] = None
    thermal_coefficient_pct: Optional[float] = None
    power_tolerance_min_pct: Optional[float] = None
    year_1_degradation_pct: Optional[float] = None
    annual_degradation_pct: Optional[float] = None
    cec_efficiency_pct: Optional[float] = None
    soiling_factor: Optional[float] = None
    dc_loss_pct: Optional[float] = None
    ac_loss_pct: Optional[float] = None
    medium_voltage_loss_pct: Optional[float] = None
    mv_line_loss_pct: Optional[float] = None
    pto_date: Optional[date] = None

    loss_assumptions_json: Optional[dict[str, Any]] = None
    model_parameters_json: Optional[dict[str, Any]] = None
    ai_confidence_json: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class ExpectedBaselineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: int
    company_id: int
    site_id: int
    baseline_name: str
    baseline_type: TelemetryBaselineType
    status: TelemetryBaselineStatus
    source_type: Optional[TelemetryBaselineSource] = None
    source_document_id: Optional[int] = None
    source_project_fact_id: Optional[int] = None

    timezone: Optional[str] = None
    system_size_ac_kw: Optional[float] = None
    system_size_dc_kw: Optional[float] = None
    degradation_rate: Optional[float] = None

    module_wattage: Optional[float] = None
    module_quantity: Optional[float] = None
    inverter_wattage: Optional[float] = None
    inverter_quantity: Optional[float] = None
    thermal_coefficient_pct: Optional[float] = None
    power_tolerance_min_pct: Optional[float] = None
    year_1_degradation_pct: Optional[float] = None
    annual_degradation_pct: Optional[float] = None
    cec_efficiency_pct: Optional[float] = None
    soiling_factor: Optional[float] = None
    dc_loss_pct: Optional[float] = None
    ac_loss_pct: Optional[float] = None
    medium_voltage_loss_pct: Optional[float] = None
    mv_line_loss_pct: Optional[float] = None
    pto_date: Optional[date] = None

    loss_assumptions_json: Optional[dict[str, Any]] = None
    model_parameters_json: Optional[dict[str, Any]] = None
    ai_confidence_json: Optional[dict[str, Any]] = None

    version: int
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    active_from: Optional[datetime] = None
    active_to: Optional[datetime] = None
    supersedes_baseline_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ExpectedBaselineListResponse(BaseModel):
    site_id: int
    baselines: list[ExpectedBaselineResponse] = Field(default_factory=list)
    # Server-computed viewer capabilities for this site (Phase 0). The frontend
    # mirrors backend authority via these flags and never re-derives company-admin
    # locally. ``viewer_can_author_draft`` = telemetry-admin + site access;
    # ``viewer_can_manage_lifecycle`` = telemetry-admin AND company-admin (or
    # platform bypass).
    viewer_can_author_draft: bool = False
    viewer_can_manage_lifecycle: bool = False


class ActiveExpectedBaselineResponse(BaseModel):
    """Active baseline for a site plus the viewer's capability flags.

    Envelopes the (nullable) active baseline so any site-visible user can still
    reach it (read access is unchanged) while learning whether they may author a
    draft or manage the lifecycle. Flags are the backend source of truth.
    """

    site_id: int
    baseline: Optional[ExpectedBaselineResponse] = None
    viewer_can_author_draft: bool = False
    viewer_can_manage_lifecycle: bool = False


class ExpectedPreviewBucket(BaseModel):
    """One bucket of an expected-vs-actual preview.

    ``status`` is ``ok`` | ``missing_inputs`` | ``pre_pto``. Expected fields are
    ``null`` (never 0) on non-``ok`` buckets.
    """

    bucket_start: datetime
    status: str
    expected_power_kw: Optional[float] = None
    expected_energy_kwh: Optional[float] = None
    actual_power_kw: Optional[float] = None
    irradiance_wm2: Optional[float] = None
    cell_temperature_f: Optional[float] = None
    age_years: Optional[int] = None


class ExpectedWeatherProvenanceSchema(BaseModel):
    """W1 provenance describing what weather drove an expected computation.

    Additive and nullable. ``source_type``/``is_modeled`` describe how the
    numeric values were produced (always the DAS stream in W1).
    ``missing_inputs`` here lists provenance/availability gaps for the WINDOW and
    is distinct from the per-bucket ``status == missing_inputs``. The resolver
    never promotes an unknown stream to high-confidence POA.
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
    missing_inputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    indicators: list[str] = Field(default_factory=list)
    # W2 additive: populated only when an APPROVED historical profile drove the
    # window from imported observations. The live DAS path leaves these at their
    # defaults (``historical=False``, no batch ids, ``coverage_pct=None``) so W1
    # responses are unchanged.
    historical: bool = False
    observation_batch_ids: list[int] = Field(default_factory=list)
    coverage_pct: Optional[float] = None


class ExpectedPreviewResponse(BaseModel):
    """Weather-adjusted expected vs. actual for a site + window.

    ``overall_status`` is ``ok`` when a baseline drove the calc, or
    ``baseline_not_available`` when no usable baseline exists (then ``buckets``
    is empty — the calc never fabricates an expected line).
    """

    site_id: int
    overall_status: str
    baseline_id: Optional[int] = None
    baseline_type: Optional[str] = None
    bucket_size: str
    window_start: datetime
    window_end: datetime
    expected_energy_kwh: Optional[float] = None
    actual_energy_kwh: Optional[float] = None
    ok_bucket_count: int = 0
    missing_inputs_bucket_count: int = 0
    pre_pto_bucket_count: int = 0
    buckets: list[ExpectedPreviewBucket] = Field(default_factory=list)
    # Additive (W1): nullable provenance for the weather inputs. ``None`` when no
    # baseline was available (no weather was resolved).
    weather_provenance: Optional[ExpectedWeatherProvenanceSchema] = None


class DraftExpectedPreviewResponse(ExpectedPreviewResponse):
    """Draft/approved expected-vs-actual preview (Phase 1, telemetry-admin only).

    Identical computation to the public preview but for an explicitly requested
    ``draft`` or ``approved`` baseline so reviewers can inspect a candidate curve
    BEFORE it is activated. It never activates, never persists, and is isolated
    from the public preview (which still rejects draft/in_review baselines). The
    additive fields make the not-yet-live nature explicit to the UI.
    """

    is_draft_preview: bool = True
    baseline_status: str
    validation_summary: Optional[dict[str, Any]] = None
    disclaimer: str = (
        "Preview of a draft/approved baseline that is NOT active. Numbers are "
        "for review only and do not affect any live expected-performance output."
    )


# ---------------------------------------------------------------------------
# DD V2 Phase 2 — promoted project_facts -> draft baseline bridge
# ---------------------------------------------------------------------------


class BaselineFactFieldUsage(BaseModel):
    """One physics input that fed (or could feed) a facts-based draft."""

    field: str
    source: str  # 'project_fact' | 'reviewer_supplied' | 'project_fact_normalized'
    value: float
    canonical_name: Optional[str] = None
    fact_id: Optional[int] = None
    document_id: Optional[int] = None
    ai_confidence: Optional[float] = None


class BaselineFieldNormalization(BaseModel):
    """A PROPOSED (never auto-applied) unit normalization for a fact value.

    Mirrors the service ``NormalizationProposal``. ``blocked`` means the value
    cannot be normalized (ambiguous/unknown unit, unparseable) and stays missing;
    a non-blocked proposal is only applied when the reviewer confirms it (and,
    for a real unit conversion, sets ``allow_conversion``).
    """

    field: str
    raw_value: str
    target_unit: str
    blocked: bool
    reason: str
    proposed_value: Optional[float] = None
    from_unit: Optional[str] = None
    method: Optional[str] = None  # 'unit_strip' | 'unit_convert'
    factor: float = 1.0
    requires_confirmation: bool = False
    requires_conversion_confirmation: bool = False


class BaselineReadinessFieldStatus(BaseModel):
    """One baseline input's true position on the readiness ladder (descriptive).

    Additive — it never changes ``ready`` semantics. The panel uses it to show
    what is usable, what needs a reviewer value or a normalization confirmation,
    and what the next step is.
    """

    field: str
    display_label: str
    required: bool
    expected_type: str  # 'number' | 'count' | 'percent' | 'factor' | 'date'
    expected_unit: Optional[str] = None
    source_status: str
    blocking_level: str
    current_raw_value: Optional[str] = None
    current_normalized_value: Optional[float] = None
    default_value: Optional[float] = None
    reason: Optional[str] = None
    recommended_action: Optional[str] = None
    fact_id: Optional[int] = None
    document_id: Optional[int] = None
    ai_confidence: Optional[float] = None
    normalization: Optional[BaselineFieldNormalization] = None


class NormalizationConfirmationRequest(BaseModel):
    """A reviewer's explicit confirmation of a proposed unit normalization.

    The server NEVER trusts ``confirmed_value`` as the value to store — it
    recomputes the normalization from the current active fact and only applies it
    when its own ``proposed_value`` matches ``confirmed_value`` (integrity check),
    the confirmation is not stale (``source_fact_id`` / ``raw_value`` match the
    current fact), and — for a real unit conversion — ``allow_conversion`` is set.
    """

    confirmed_value: float
    unit: Optional[str] = None
    allow_conversion: bool = False
    # Both anchors are REQUIRED. A normalization is applied only when the
    # confirmation can be proven current against the live fact, so omitting
    # either anchor is rejected outright — the server never applies an
    # unanchored (unprovable) normalization.
    source_fact_id: int
    raw_value: str


class ReadinessFromFactsResponse(BaseModel):
    """Whether a site's promoted facts can produce a weather-adjusted draft.

    ``ready`` is True only when every required physics field is satisfied.
    Reviewer-only datasheet constants are always reported as ``missing_fields``
    here (they are supplied on the create request), so ``ready`` is typically
    False until they are provided. Nothing is ever fabricated.
    """

    site_id: int
    baseline_type: TelemetryBaselineType
    ready: bool
    fields_used: list[BaselineFactFieldUsage] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_fact_ids: list[int] = Field(default_factory=list)
    source_document_ids: list[int] = Field(default_factory=list)
    # Additive: per-field readiness ladder (descriptive; never changes ``ready``).
    field_blockers: list[BaselineReadinessFieldStatus] = Field(default_factory=list)


class CreateDraftFromFactsRequest(BaseModel):
    """Create a draft baseline from promoted facts + reviewer-supplied constants.

    Module / inverter wattage + quantity come from promoted ``project_facts`` and
    are NOT accepted here (facts are the source of truth). The reviewer supplies
    the datasheet constants that have no fact source; loss %, soiling and PTO are
    optional (the calc has safe defaults). Percent-valued fields are PERCENT.
    """

    model_config = ConfigDict(protected_namespaces=())

    baseline_type: TelemetryBaselineType = TelemetryBaselineType.weather_adjusted_model
    baseline_name: Optional[str] = Field(default=None, max_length=255)
    reason: Optional[str] = None

    # Required datasheet constants (no fact source exists today).
    thermal_coefficient_pct: Optional[float] = None
    power_tolerance_min_pct: Optional[float] = None
    year_1_degradation_pct: Optional[float] = None
    annual_degradation_pct: Optional[float] = None
    cec_efficiency_pct: Optional[float] = None

    # Optional supplemental — absence is a warning, not a blocker.
    soiling_factor: Optional[float] = None
    dc_loss_pct: Optional[float] = None
    ac_loss_pct: Optional[float] = None
    medium_voltage_loss_pct: Optional[float] = None
    mv_line_loss_pct: Optional[float] = None
    pto_date: Optional[date] = None

    # Reviewer-confirmed unit normalizations for unit-qualified facts, keyed by
    # canonical column (``module_wattage`` / ``inverter_wattage``). Each entry is
    # re-verified server-side against a fresh recompute; the front end's value is
    # never trusted blindly. Facts are never mutated.
    normalizations: Optional[dict[str, NormalizationConfirmationRequest]] = None


class BaselineActivateRequest(BaseModel):
    """Optional body for the activate endpoint, carrying the warning-ack waiver.

    Both fields default to the no-waiver case so an existing caller that POSTs no
    body still works. ``acknowledge_warnings`` (with a non-empty
    ``activation_source_note``) is REQUIRED only when the baseline has
    ``warning``-level fields; it can never waive a ``hard_invalid`` verdict.
    """

    acknowledge_warnings: bool = False
    activation_source_note: Optional[str] = Field(default=None, max_length=2000)


class CreateDraftFromFactsResponse(BaseModel):
    """Result of a create-draft-from-facts attempt.

    ``status`` is ``draft`` when a draft exists (newly created or reused) or
    ``review_required`` when required fields are missing (then no row is created
    and the endpoint returns 422 with this body).
    """

    site_id: int
    baseline_type: TelemetryBaselineType
    ready: bool
    status: str
    draft_baseline_id: Optional[int] = None
    created: bool = False
    idempotent_existing: bool = False
    fields_used: list[BaselineFactFieldUsage] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_fact_ids: list[int] = Field(default_factory=list)
    source_document_ids: list[int] = Field(default_factory=list)
    # Additive: per-field readiness ladder (descriptive; never changes ``ready``).
    field_blockers: list[BaselineReadinessFieldStatus] = Field(default_factory=list)
    baseline: Optional[ExpectedBaselineResponse] = None


class BaselineFieldDiff(BaseModel):
    """One physics field's old→new comparison between two baselines.

    ``old_value`` / ``new_value`` are numeric (``None`` for the date-valued PTO,
    whose values live in ``*_display``). ``source`` is the documented provenance
    class (``project_facts`` for fact-backed module/inverter fields,
    ``reviewer_constant`` for datasheet constants/losses/PTO, ``derived`` for the
    system-size summaries). The validation fields carry the PROPOSED baseline's
    per-field verdict (read-only).
    """

    field: str
    label: str
    unit: Optional[str] = None
    old_value: Optional[float] = None
    new_value: Optional[float] = None
    old_display: Optional[str] = None
    new_display: Optional[str] = None
    changed: bool
    source: str
    new_validation_classification: Optional[str] = None
    new_validation_reason: Optional[str] = None


class BaselineExpectedImpact(BaseModel):
    """Reference-condition illustration of the expected-power change.

    Computed via the SAME canonical breakdown production uses, at a fixed
    partial-load, hot operating point (below typical inverter clipping) where the
    temperature coefficient is material and parameter differences stay visible. It
    is an illustration of how the two parameter sets differ at that point — NOT a
    forecast and NOT a recompute of any stored curve. ``None`` power values appear
    when a baseline lacks the required physics fields.
    """

    reference_irradiance_wm2: float
    reference_cell_temperature_c: float
    reference_age_years: int
    old_expected_power_kw: Optional[float] = None
    new_expected_power_kw: Optional[float] = None
    delta_kw: Optional[float] = None
    delta_pct: Optional[float] = None
    note: str


class BaselineDiffResponse(BaseModel):
    """Side-by-side diff of a proposed replacement vs the baseline it replaces.

    ``from`` is the baseline being replaced (the site's current ACTIVE one by
    default) and ``to`` is the proposed replacement. Carries the FULL fail-closed
    validation verdict for BOTH so an invalid active baseline and a valid
    replacement are both visible. Read-only — the endpoint performs zero writes.
    """

    site_id: int
    from_baseline_id: Optional[int] = None
    from_status: Optional[str] = None
    to_baseline_id: int
    to_status: Optional[str] = None
    changed_fields: list[BaselineFieldDiff] = Field(default_factory=list)
    unchanged_fields: list[BaselineFieldDiff] = Field(default_factory=list)
    from_validation: Optional[dict[str, Any]] = None
    to_validation: dict[str, Any] = Field(default_factory=dict)
    expected_impact: Optional[BaselineExpectedImpact] = None


# ---------------------------------------------------------------------------
# DD V2 Phase 3 — design-estimate baseline POINTS producer
# ---------------------------------------------------------------------------
class DesignPointsReadinessResponse(BaseModel):
    """Whether a draft baseline's design-estimate points can be produced.

    Read-only preview: ``ready`` is True only when at least one production fact is
    present, all PRESENT production facts parse, and a reference year can be
    anchored. Absent months are reported as "partial" (a warning), never an error;
    a present-but-malformed value is an itemized ``parse_errors`` entry. GHI and
    P50/P90 are surfaced under ``scenarios`` (the point schema cannot store them).
    Nothing is ever fabricated and the GET never writes.
    """

    model_config = ConfigDict(protected_namespaces=())

    site_id: int
    baseline_id: int
    baseline_type: TelemetryBaselineType
    ready: bool
    has_design_data: bool
    parsed_months: list[int] = Field(default_factory=list)
    monthly_points_planned: int = 0
    annual_value: Optional[float] = None
    annual_point_planned: bool = False
    reference_year: Optional[int] = None
    reference_year_source: Optional[str] = None
    missing_fields: list[str] = Field(default_factory=list)
    parse_errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scenarios: Optional[dict[str, Any]] = None
    schema_expansion_recommended: bool = False
    source_fact_ids: list[int] = Field(default_factory=list)
    source_document_ids: list[int] = Field(default_factory=list)


class GenerateDesignPointsResponse(BaseModel):
    """Result of a generate/rebuild of a baseline's design-estimate points.

    ``status`` is ``generated`` when points were (re)written, ``no_design_data``
    when no production fact exists, or ``malformed`` when a present production fact
    failed to parse. In the latter two cases nothing is written and the endpoint
    returns 422 with this body. The rebuild is idempotent: re-running with the same
    facts deletes the prior monthly/annual points and re-inserts an identical set.
    """

    model_config = ConfigDict(protected_namespaces=())

    site_id: int
    baseline_id: int
    baseline_type: TelemetryBaselineType
    ready: bool
    status: str
    parsed_months: list[int] = Field(default_factory=list)
    annual_value: Optional[float] = None
    reference_year: Optional[int] = None
    reference_year_source: Optional[str] = None
    points_created: int = 0
    points_deleted: int = 0
    monthly_points: int = 0
    annual_points: int = 0
    missing_fields: list[str] = Field(default_factory=list)
    parse_errors: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scenarios: Optional[dict[str, Any]] = None
    schema_expansion_recommended: bool = False
    source_fact_ids: list[int] = Field(default_factory=list)
    source_document_ids: list[int] = Field(default_factory=list)
