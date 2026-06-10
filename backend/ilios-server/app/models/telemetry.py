import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class DASProvidersEnum(enum.Enum):
    kmc = "KMC"
    also_energy = "Also Energy"


# ---------------------------------------------------------------------------
# Telemetry v2 enums (Phase 1 introduce — additive)
# ---------------------------------------------------------------------------


class ProviderAccountStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class CredentialStatus(str, enum.Enum):
    unverified = "unverified"
    verified = "verified"
    invalid = "invalid"
    expired = "expired"


class LastSyncStatus(str, enum.Enum):
    never = "never"
    success = "success"
    partial = "partial"
    failed = "failed"


class ExternalSiteSyncStatus(str, enum.Enum):
    seen = "seen"
    missing = "missing"
    stale = "stale"


class CompanyProviderStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"


# ---------------------------------------------------------------------------
# Telemetry provider catalog (DB-backed registry)
# ---------------------------------------------------------------------------


class TelemetryProviderCatalog(Base):
    __tablename__ = "telemetry_provider_catalog"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    provider_key = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(128), nullable=False)
    adapter_class = Column(String(255), nullable=False)
    config_schema = Column(JSONB, nullable=False, default=dict)
    docs_url = Column(String(512), nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    licenses = relationship("CompanyDASProvider", back_populates="catalog")


# ---------------------------------------------------------------------------
# Company licenses (m:n catalog ↔ company)
# ---------------------------------------------------------------------------


class CompanyDASProvider(Base):
    __tablename__ = "company_das_providers"
    __table_args__ = (
        UniqueConstraint("company_id", "provider", name="uq_company_das_provider"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Enum(DASProvidersEnum), nullable=False)

    # ---- v2 additive fields ----
    catalog_id = Column(
        Integer,
        ForeignKey("telemetry_provider_catalog.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status = Column(
        Enum(CompanyProviderStatus, name="company_provider_status_enum"),
        nullable=False,
        default=CompanyProviderStatus.active,
        server_default=CompanyProviderStatus.active.value,
    )
    notes = Column(String(1000), nullable=True)
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    created_at = Column(DateTime, server_default=utcnow())

    company = relationship("Company", back_populates="das_providers")
    catalog = relationship("TelemetryProviderCatalog", back_populates="licenses")
    accounts = relationship("DASConnection", back_populates="company_provider")


class DASConnectionOwnerType(enum.Enum):
    company = "company"
    portfolio = "portfolio"


# ---------------------------------------------------------------------------
# Provider account (DASConnection)
# ---------------------------------------------------------------------------


class DASConnection(Base):
    __tablename__ = "das_connections"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    provider = Column(Enum(DASProvidersEnum), nullable=False)
    secret_token_name = Column(String, nullable=False)

    owner_type = Column(String(20), nullable=False, default="company")
    owner_company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)

    last_test_at = Column(DateTime, nullable=True)
    last_test_status = Column(String(20), nullable=True)
    last_test_message = Column(String(500), nullable=True)

    # ---- v2 additive fields ----
    company_provider_id = Column(
        Integer,
        ForeignKey("company_das_providers.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status = Column(
        Enum(ProviderAccountStatus, name="provider_account_status_enum"),
        nullable=False,
        default=ProviderAccountStatus.active,
        server_default=ProviderAccountStatus.active.value,
    )
    credential_status = Column(
        Enum(CredentialStatus, name="credential_status_enum"),
        nullable=False,
        default=CredentialStatus.unverified,
        server_default=CredentialStatus.unverified.value,
    )
    last_sync_status = Column(
        Enum(LastSyncStatus, name="last_sync_status_enum"),
        nullable=False,
        default=LastSyncStatus.never,
        server_default=LastSyncStatus.never.value,
    )
    external_account_label = Column(String(255), nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_error_at = Column(DateTime, nullable=True)
    last_error_message = Column(String(1000), nullable=True)
    is_archived = Column(Boolean, nullable=False, default=False, server_default="false")
    archived_at = Column(DateTime, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    company = relationship("Company", back_populates="das_connections", foreign_keys=[company_id])
    owner_company = relationship("Company", foreign_keys=[owner_company_id])
    site_mapping = relationship(
        "TelemetrySiteMapping",
        back_populates="connection",
        uselist=False,
        foreign_keys="TelemetrySiteMapping.connection_id",
    )

    # v2 relationships
    company_provider = relationship("CompanyDASProvider", back_populates="accounts")
    external_sites = relationship(
        "TelemetryExternalSite",
        back_populates="provider_account",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    external_devices = relationship(
        "TelemetryExternalDevice",
        back_populates="provider_account",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------------
# Synced external sites (provenance for sync runs)
# ---------------------------------------------------------------------------


class TelemetryExternalSite(Base):
    __tablename__ = "telemetry_external_sites"
    __table_args__ = (
        UniqueConstraint(
            "provider_account_id",
            "external_site_id",
            name="uq_telemetry_external_sites_account_extid",
        ),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    provider_account_id = Column(
        Integer,
        ForeignKey("das_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_site_id = Column(String(255), nullable=False)
    external_site_name = Column(String(512), nullable=True)
    raw_metadata = Column(JSONB, nullable=True)

    first_seen_at = Column(DateTime, nullable=False, server_default=utcnow())
    last_seen_at = Column(DateTime, nullable=False, server_default=utcnow())
    last_synced_at = Column(DateTime, nullable=False, server_default=utcnow())
    last_sync_run_id = Column(String(64), nullable=True)
    sync_status = Column(
        Enum(ExternalSiteSyncStatus, name="external_site_sync_status_enum"),
        nullable=False,
        default=ExternalSiteSyncStatus.seen,
        server_default=ExternalSiteSyncStatus.seen.value,
    )
    last_sync_error = Column(String(1000), nullable=True)

    provider_account = relationship("DASConnection", back_populates="external_sites")


# ---------------------------------------------------------------------------
# Synced external devices (per-site hardware cache for sync runs)
# ---------------------------------------------------------------------------


class TelemetryExternalDevice(Base):
    """DB-backed cache of the devices a provider reports for one external site.

    This mirrors :class:`TelemetryExternalSite` one level down: a device row is
    uniquely identified by ``{provider_account_id, external_site_id,
    external_device_id}``. The V2 Device Mapping step reads from this cache so
    opening the step never requires a live provider call when the account has
    already been synced. Rows are upserted by the explicit ``sync-devices``
    route and are never wiped on a provider/sync failure.
    """

    __tablename__ = "telemetry_external_devices"
    __table_args__ = (
        UniqueConstraint(
            "provider_account_id",
            "external_site_id",
            "external_device_id",
            name="uq_telemetry_external_devices_account_site_device",
        ),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    provider_account_id = Column(
        Integer,
        ForeignKey("das_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_site_id = Column(String(255), nullable=False)
    external_device_id = Column(String(255), nullable=False)
    external_device_name = Column(String(512), nullable=True)
    raw_metadata = Column(JSONB, nullable=True)

    first_seen_at = Column(DateTime, nullable=False, server_default=utcnow())
    last_seen_at = Column(DateTime, nullable=False, server_default=utcnow())
    last_synced_at = Column(DateTime, nullable=False, server_default=utcnow())
    last_sync_run_id = Column(String(64), nullable=True)
    sync_status = Column(
        Enum(ExternalSiteSyncStatus, name="external_site_sync_status_enum"),
        nullable=False,
        default=ExternalSiteSyncStatus.seen,
        server_default=ExternalSiteSyncStatus.seen.value,
    )
    last_sync_error = Column(String(1000), nullable=True)

    provider_account = relationship("DASConnection", back_populates="external_devices")


# ---------------------------------------------------------------------------
# Site / device mappings (m:n with role)
# ---------------------------------------------------------------------------


class TelemetrySiteMapping(Base):
    __tablename__ = "telemetry_sites_mapping"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), unique=True)
    connection_id = Column(Integer, ForeignKey("das_connections.id", ondelete="SET NULL"))

    telemetry_site_id = Column(String, nullable=False)
    telemetry_site_name = Column(String, nullable=False)

    # ---- v2 additive fields ----
    provider_account_id = Column(
        Integer,
        ForeignKey("das_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    mapping_role = Column(String(32), nullable=False, default="primary", server_default="primary")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    site = relationship("Site", back_populates="telemetry_mapping")
    connection = relationship("DASConnection", back_populates="site_mapping", foreign_keys=[connection_id])
    provider_account = relationship("DASConnection", foreign_keys=[provider_account_id])

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())


class TelemetryDeviceMapping(Base):
    __tablename__ = "telemetry_devices_mapping"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False)

    telemetry_device_id = Column(String, nullable=False)
    telemetry_device_name = Column(String, nullable=False)

    # ---- v2 additive fields ----
    provider_account_id = Column(
        Integer,
        ForeignKey("das_connections.id", ondelete="SET NULL"),
        nullable=True,
    )
    device_role = Column(String(32), nullable=False, default="primary", server_default="primary")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")

    device = relationship("Device", back_populates="telemetry_mapping")
    provider_account = relationship("DASConnection", foreign_keys=[provider_account_id])

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())


# ---------------------------------------------------------------------------
# Native V2 ingestion enums (Phase: native ingestion + manual refresh)
# ---------------------------------------------------------------------------


class TelemetrySyncStatus(str, enum.Enum):
    """Lifecycle of a single ingestion attempt (mirrors ``finance_sync_runs``).

    ``partial`` is the V2 addition: some device/metric pulls succeeded while
    others failed within the same run. It is distinct from ``failed`` (nothing
    written) and ``succeeded`` (no per-target errors).
    """

    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    partial = "partial"
    failed = "failed"


class TelemetrySyncScope(str, enum.Enum):
    """Scope a sync job targets.

    Only ``site`` is executed today. ``company`` / ``portfolio`` exist so the
    follow-up scheduler/backfill task can reuse the same table and service with
    a wider scope without a schema change.
    """

    site = "site"
    company = "company"
    portfolio = "portfolio"


class TelemetrySyncTrigger(str, enum.Enum):
    """What initiated a sync job."""

    manual = "manual"
    scheduled = "scheduled"
    backfill = "backfill"


# ---------------------------------------------------------------------------
# Metric catalog (provider field -> normalized metric)
# ---------------------------------------------------------------------------


class TelemetryMetricCatalog(Base):
    """Maps a provider's raw point/field to a normalized iliOS metric.

    Seeded from the legacy AlsoEnergy point-tag map. Each row is the unit of
    "pull this field, store it as this normalized metric".

    Two provider field names are tracked because AlsoEnergy uses different
    identifiers for discovery vs. query:

    * ``provider_field_name`` — the name that appears in a device's
      ``fieldsArchived`` list (the legacy short name, e.g. ``KwAC``). This is
      what the ingestion service intersects with a device's available fields,
      and what the BinData response echoes back in ``info[0].name``.
    * ``provider_query_field`` — the canonical field name sent as the BinData
      request ``fieldName`` (e.g. ``Active_Power``). Replicates the legacy
      contract exactly; nothing about the provider API is invented here.

    Multiple rows may share a ``normalized_metric`` (e.g. AlsoEnergy ``Sun`` ->
    POA and ``Sun2`` -> GHI both normalize to ``irradiance_wm2``). When a single
    device exposes more than one provider field for the same normalized metric
    the pull is *ambiguous* and is skipped for that device — mirroring the
    legacy pipeline behaviour.
    """

    __tablename__ = "telemetry_metric_catalog"
    __table_args__ = (
        UniqueConstraint(
            "provider_key",
            "provider_field_name",
            name="uq_telemetry_metric_catalog_provider_field",
        ),
        Index("ix_telemetry_metric_catalog_provider", "provider_key"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    provider_key = Column(String(64), nullable=False)
    provider_field_name = Column(String(255), nullable=False)
    provider_query_field = Column(String(255), nullable=True)
    normalized_metric = Column(String(64), nullable=False)
    unit = Column(String(32), nullable=False)
    device_category = Column(String(64), nullable=True)
    is_enabled = Column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())


# ---------------------------------------------------------------------------
# Sync jobs (one row per ingestion attempt)
# ---------------------------------------------------------------------------


class TelemetrySyncJob(Base):
    """One ingestion attempt. Mirrors ``finance_sync_runs`` with telemetry
    specifics (scope/trigger/window + per-device stats).

    A row is created for *every* attempt — including provider failures — so the
    UI can surface a "last refreshed" timestamp and an error without inspecting
    raw readings. A failed run never deletes mappings, cached devices, or
    previously stored readings.
    """

    __tablename__ = "telemetry_sync_jobs"
    __table_args__ = (
        Index("ix_telemetry_sync_jobs_company", "company_id"),
        Index("ix_telemetry_sync_jobs_site", "site_id"),
        Index("ix_telemetry_sync_jobs_status", "status"),
        Index("ix_telemetry_sync_jobs_started_at", "started_at"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    provider_account_id = Column(
        Integer, ForeignKey("das_connections.id", ondelete="SET NULL"), nullable=True
    )
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True
    )
    scope = Column(
        Enum(TelemetrySyncScope, name="telemetry_sync_scope_enum"),
        nullable=False,
        default=TelemetrySyncScope.site,
        server_default=TelemetrySyncScope.site.value,
    )
    status = Column(
        Enum(TelemetrySyncStatus, name="telemetry_sync_status_enum"),
        nullable=False,
        default=TelemetrySyncStatus.queued,
        server_default=TelemetrySyncStatus.queued.value,
    )
    trigger = Column(
        Enum(TelemetrySyncTrigger, name="telemetry_sync_trigger_enum"),
        nullable=False,
        default=TelemetrySyncTrigger.manual,
        server_default=TelemetrySyncTrigger.manual.value,
    )
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)
    correlation_id = Column(String(64), nullable=False)
    triggered_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    records_requested = Column(Integer, nullable=False, default=0, server_default="0")
    records_received = Column(Integer, nullable=False, default=0, server_default="0")
    records_written = Column(Integer, nullable=False, default=0, server_default="0")
    last_error = Column(Text, nullable=True)
    stats_json = Column(JSONB, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())
    updated_at = Column(
        DateTime, nullable=False, server_default=utcnow(), onupdate=utcnow()
    )


# ---------------------------------------------------------------------------
# Readings (normalized source of truth)
# ---------------------------------------------------------------------------


class TelemetryReading(Base):
    """A single normalized reading, carrying the full provenance hierarchy:

    company -> provider account -> external site -> iliOS site ->
    external device -> iliOS device -> normalized metric.

    Idempotency: re-pulling the same window must not create duplicates. The
    dedupe key is ``(provider_account_id, dedupe_key, provider_metric,
    metric_ts)``. ``external_device_id`` is kept nullable for fidelity (a
    provider could one day report a site-level point with no device), but
    Postgres treats NULLs as distinct in unique constraints, which would defeat
    idempotency. ``dedupe_key`` is therefore a NOT NULL projection of the
    external device id (falling back to the ``__site__`` sentinel) used solely
    for the upsert conflict target.

    Timestamps are stored as UTC-naive ``DateTime`` to match the rest of the
    schema. ``device_id`` is null for devices the provider returns that are not
    mapped to an iliOS device.
    """

    __tablename__ = "telemetry_readings"
    __table_args__ = (
        UniqueConstraint(
            "provider_account_id",
            "dedupe_key",
            "provider_metric",
            "metric_ts",
            name="uq_telemetry_readings_dedupe",
        ),
        Index("ix_telemetry_readings_site_ts", "site_id", "metric_ts"),
        Index("ix_telemetry_readings_device_ts", "device_id", "metric_ts"),
        Index("ix_telemetry_readings_sync_job", "sync_job_id"),
    )

    id = Column(BigInteger, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    provider_account_id = Column(
        Integer, ForeignKey("das_connections.id", ondelete="SET NULL"), nullable=True
    )
    external_site_id = Column(String(255), nullable=False)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    external_device_id = Column(String(255), nullable=True)
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    dedupe_key = Column(String(255), nullable=False)

    provider_key = Column(String(64), nullable=False)
    provider_metric = Column(String(255), nullable=False)
    normalized_metric = Column(String(64), nullable=False)
    metric_ts = Column(DateTime, nullable=False)
    value = Column(Numeric, nullable=False)
    unit = Column(String(32), nullable=True)
    quality = Column(String(32), nullable=True)

    sync_job_id = Column(
        Integer,
        ForeignKey("telemetry_sync_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime, nullable=False, server_default=utcnow())

    SITE_LEVEL_SENTINEL = "__site__"


# ---------------------------------------------------------------------------
# Interval rollups (derived; idempotent per window)
# ---------------------------------------------------------------------------


class TelemetrySiteIntervalRollup(Base):
    """Per-site, per-metric time-bucket aggregate.

    Lets dashboards read pre-aggregated intervals without rescanning raw
    readings. Idempotent per window: re-running a refresh upserts the same
    ``(site_id, bucket_start, bucket_size, normalized_metric)`` row. A rollup
    failure never deletes raw readings.
    """

    __tablename__ = "telemetry_site_interval_rollups"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "bucket_start",
            "bucket_size",
            "normalized_metric",
            name="uq_telemetry_site_rollup",
        ),
        Index("ix_telemetry_site_rollup_site_bucket", "site_id", "bucket_start"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    bucket_start = Column(DateTime, nullable=False)
    bucket_size = Column(String(16), nullable=False)
    normalized_metric = Column(String(64), nullable=False)
    agg = Column(String(16), nullable=False)
    value = Column(Numeric, nullable=False)
    unit = Column(String(32), nullable=True)
    sample_count = Column(Integer, nullable=False, default=0, server_default="0")
    completeness = Column(Numeric, nullable=True)
    calculated_at = Column(DateTime, nullable=False, server_default=utcnow())


class TelemetryDeviceIntervalRollup(Base):
    """Per-device, per-metric time-bucket aggregate. Same shape as
    :class:`TelemetrySiteIntervalRollup` but keyed by ``device_id``.
    """

    __tablename__ = "telemetry_device_interval_rollups"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "bucket_start",
            "bucket_size",
            "normalized_metric",
            name="uq_telemetry_device_rollup",
        ),
        Index("ix_telemetry_device_rollup_device_bucket", "device_id", "bucket_start"),
        Index("ix_telemetry_device_rollup_site", "site_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    bucket_start = Column(DateTime, nullable=False)
    bucket_size = Column(String(16), nullable=False)
    normalized_metric = Column(String(64), nullable=False)
    agg = Column(String(16), nullable=False)
    value = Column(Numeric, nullable=False)
    unit = Column(String(32), nullable=True)
    sample_count = Column(Integer, nullable=False, default=0, server_default="0")
    completeness = Column(Numeric, nullable=True)
    calculated_at = Column(DateTime, nullable=False, server_default=utcnow())


# ---------------------------------------------------------------------------
# Scheduler state (one row per mapped site/provider account)
# ---------------------------------------------------------------------------


class TelemetrySchedulerState(Base):
    """Per-(site, provider account) automation state for native V2 telemetry.

    Drives the in-process scheduler runner and the bounded backfill endpoint.
    Both triggers reuse the *same* ingestion + rollup services as the manual
    Refresh Telemetry action; this table only carries scheduling metadata and a
    DB-backed lock so overlapping runs for the same site cannot start.

    Rows are created lazily on the first enable/backfill — there is no migration
    seed, so new site mappings created after the migration get the same lazy
    path. ``last_status`` is a free string (not the sync-status enum) because it
    must also be able to hold ``config_error`` (raised before any sync job row
    exists) and ``skipped``.

    Cursor contract: ``last_successful_pull_at`` advances ONLY when a scheduled
    run's readings upsert AND rollup both succeed. Backfill never touches it.

    Overlap contract: ``lock_token``/``locked_until`` form a lease-based claim.
    A run claims the row with an atomic conditional UPDATE; a crashed run's lease
    self-expires so the row is reclaimable without manual intervention.
    """

    __tablename__ = "telemetry_scheduler_state"
    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "provider_account_id",
            name="uq_telemetry_scheduler_state_site_account",
        ),
        Index(
            "ix_telemetry_scheduler_state_due",
            "enabled",
            "next_due_at",
        ),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    provider_account_id = Column(
        Integer,
        ForeignKey("das_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    # ISO-8601 duration from a fixed whitelist (PT15M/PT30M/PT1H/PT6H/PT24H).
    cadence = Column(
        String(16), nullable=False, default="PT1H", server_default="PT1H"
    )
    last_run_at = Column(DateTime, nullable=True)
    last_successful_pull_at = Column(DateTime, nullable=True)
    # Free string: succeeded/partial/failed/skipped/config_error.
    last_status = Column(String(16), nullable=True)
    last_error = Column(Text, nullable=True)
    last_sync_job_id = Column(
        Integer,
        ForeignKey("telemetry_sync_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    next_due_at = Column(DateTime, nullable=True)
    lock_token = Column(String(64), nullable=True)
    locked_until = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())
    updated_at = Column(
        DateTime, nullable=False, server_default=utcnow(), onupdate=utcnow()
    )
