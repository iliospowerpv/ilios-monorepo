import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    String,
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
