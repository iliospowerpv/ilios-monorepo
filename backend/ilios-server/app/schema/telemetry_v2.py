"""Pydantic schemas for the v2 telemetry API.

Credential fields are write-only — they are accepted on create/update payloads
but never appear on response schemas. The three-state account model
(``status``, ``credential_status``, ``last_sync_status``) is exposed on
account responses without ever leaking credential values.
"""
from __future__ import annotations

from datetime import datetime
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
