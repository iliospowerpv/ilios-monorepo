"""Weather Data Architecture — W0 native weather provenance foundation.

This module adds an auditable *weather domain* that COEXISTS beside the existing
V2 telemetry stack; it does NOT replace ``telemetry_readings`` / the interval
rollups. Live DAS weather keeps flowing through V2 telemetry exactly as before.
These tables add the things telemetry alone cannot express:

* **source identity** (``weather_sources``) — what produced a weather value, and
  whether it is measured or modeled (no secrets/API keys live here);
* **effective-period source policy** (``weather_source_profiles``) — which source
  drives weather for a site over a date range, versioned by NEW ROW (never
  mutated) with an explicit approval lifecycle and no auto-activation;
* **import provenance** (``weather_observation_batches``) — immutable record of an
  import/pull;
* **non-telemetry weather values** (``weather_observations``) — imported, modeled
  or manual weather, append/idempotent by ``dedupe_key`` (NOT a replacement for
  ``telemetry_readings``);
* **approval ledger** (``weather_source_approvals``) — append-only audit trail;
* **measurement semantics for telemetry/device weather**
  (``weather_device_mappings``) — declares the irradiance plane / temperature type
  / calibration status of a stream. Existing DAS weather defaults to ``unknown``
  semantics until explicitly mapped — we never assume ``irradiance_wm2`` is POA;
* **expected-calc weather provenance** (``expected_weather_provenance``) — a
  forward placeholder for snapshotting which weather source drove an expected
  computation. It is DEFINED here but NOTHING writes to it in W0.

W0 invariants (see ``.local/session_plan.md`` and the approved design):
* No change to ``expected_service`` physics math, telemetry ingestion, O&M charts,
  the scheduler, due diligence, baselines, or reconciliation.
* No external weather provider, no secrets, no BigQuery/Firestore/legacy refs.
* Measurement semantics are explicit: irradiance plane and temperature type
  default to ``unknown`` and are never guessed; GHI/DNI/DHI are NOT converted to
  POA and ambient temperature is NOT converted to cell/module temperature in W0.
* Modeled weather is flagged (``is_modeled``) and never silently substituted; a
  profile must opt in via ``external_modeled_allowed`` before fallback is allowed.
"""
import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Enum,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm.attributes import get_history

from app.db.base_class import Base
from app.db.weather_declaration_guard import assert_governed_update_allowed
from app.models.helpers import utcnow


# ---------------------------------------------------------------------------
# Enums (Python str-enums; one named Postgres type each, reused across columns)
# ---------------------------------------------------------------------------
class WeatherSourceType(str, enum.Enum):
    """Taxonomy of where a weather value originates."""

    on_site_calibrated_sensor = "on_site_calibrated_sensor"
    on_site_weather_station = "on_site_weather_station"
    das_provider_stream = "das_provider_stream"
    external_modeled_provider = "external_modeled_provider"
    imported_historical_provider_file = "imported_historical_provider_file"
    imported_weather_station_file = "imported_weather_station_file"
    pvsyst_design_weather = "pvsyst_design_weather"
    manual_approved_weather_assumption = "manual_approved_weather_assumption"
    unavailable = "unavailable"


class WeatherSourceProfileRole(str, enum.Enum):
    """How a profile entry participates in weather resolution."""

    live = "live"
    historical = "historical"
    design = "design"
    fallback = "fallback"


class WeatherSourceProfileStatus(str, enum.Enum):
    """Approval lifecycle for a profile row. No auto-activation in W0/W1."""

    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    active = "active"
    superseded = "superseded"
    rejected = "rejected"


class WeatherObservationBatchKind(str, enum.Enum):
    """How a batch of weather observations was produced."""

    file_import = "file_import"
    provider_pull = "provider_pull"
    manual = "manual"
    telemetry_backfill = "telemetry_backfill"


class WeatherIrradiancePlane(str, enum.Enum):
    """Irradiance plane tag. ``unknown`` is explicit, never guessed; only ``poa``
    is physics-usable today (no transposition model is built in W0)."""

    poa = "poa"
    ghi = "ghi"
    dni = "dni"
    dhi = "dhi"
    unknown = "unknown"


class WeatherTemperatureType(str, enum.Enum):
    """Temperature semantics tag. ``ambient`` is NOT converted to cell/module in
    W0; ``unknown`` is explicit, never guessed."""

    cell = "cell"
    module = "module"
    ambient = "ambient"
    modeled_cell = "modeled_cell"
    unknown = "unknown"


class WeatherConfidence(str, enum.Enum):
    """Coarse confidence band for a weather value or a profile policy floor."""

    high = "high"
    medium = "medium"
    low = "low"
    unknown = "unknown"


class WeatherCalibrationStatus(str, enum.Enum):
    """Calibration state of a mapped weather device/stream."""

    calibrated = "calibrated"
    uncalibrated = "uncalibrated"
    expired = "expired"
    unknown = "unknown"


class WeatherDeclarationBasis(str, enum.Enum):
    """On what evidence a governed weather-semantics declaration rests (WS.1).

    Only ``provider_confirmed`` and ``source_document`` can ever make a
    declaration production-grade ``expected_model_eligible``; reviewer notes and
    assumptions are valid governed records but stay *recorded-only*.
    """

    provider_confirmed = "provider_confirmed"
    source_document = "source_document"
    reviewer_source_note = "reviewer_source_note"
    reviewer_assumption = "reviewer_assumption"


class WeatherDeclarationStatus(str, enum.Enum):
    """Lifecycle of a governed weather-semantics declaration (WS.1).

    ``needs_re_review`` is intentionally NOT a status — it is a boolean flag (with
    ``re_review_reason``) on an otherwise-``active`` row. A NULL status marks a
    legacy/ungoverned mapping that predates this governance layer.
    """

    draft = "draft"
    active = "active"
    superseded = "superseded"


class WeatherApprovalTargetType(str, enum.Enum):
    """What a weather approval ledger entry refers to."""

    profile = "profile"
    batch = "batch"
    weather_device_mapping = "weather_device_mapping"


class WeatherApprovalAction(str, enum.Enum):
    """An action recorded in the immutable weather approval ledger."""

    approve = "approve"
    reject = "reject"
    revoke = "revoke"
    supersede = "supersede"
    declare_draft = "declare_draft"
    activate = "activate"
    needs_re_review = "needs_re_review"


# Postgres enum type names (kept in lockstep with the migration constants).
WEATHER_SOURCE_TYPE_ENUM_NAME = "weather_source_type_enum"
WEATHER_PROFILE_ROLE_ENUM_NAME = "weather_source_profile_role_enum"
WEATHER_PROFILE_STATUS_ENUM_NAME = "weather_source_profile_status_enum"
WEATHER_BATCH_KIND_ENUM_NAME = "weather_observation_batch_kind_enum"
WEATHER_IRRADIANCE_PLANE_ENUM_NAME = "weather_irradiance_plane_enum"
WEATHER_TEMPERATURE_TYPE_ENUM_NAME = "weather_temperature_type_enum"
WEATHER_CONFIDENCE_ENUM_NAME = "weather_confidence_enum"
WEATHER_CALIBRATION_STATUS_ENUM_NAME = "weather_calibration_status_enum"
WEATHER_APPROVAL_TARGET_TYPE_ENUM_NAME = "weather_approval_target_type_enum"
WEATHER_APPROVAL_ACTION_ENUM_NAME = "weather_approval_action_enum"
WEATHER_DECLARATION_BASIS_ENUM_NAME = "weather_declaration_basis_enum"
WEATHER_DECLARATION_STATUS_ENUM_NAME = "weather_declaration_status_enum"

# Reusable SQLAlchemy Enum type objects. A single instance per named type is
# shared across columns/tables so ``Base.metadata.create_all`` (tests) emits one
# CREATE TYPE per name; the migration creates them explicitly with create_type.
_SOURCE_TYPE_ENUM = Enum(WeatherSourceType, name=WEATHER_SOURCE_TYPE_ENUM_NAME)
_PROFILE_ROLE_ENUM = Enum(WeatherSourceProfileRole, name=WEATHER_PROFILE_ROLE_ENUM_NAME)
_PROFILE_STATUS_ENUM = Enum(
    WeatherSourceProfileStatus, name=WEATHER_PROFILE_STATUS_ENUM_NAME
)
_BATCH_KIND_ENUM = Enum(WeatherObservationBatchKind, name=WEATHER_BATCH_KIND_ENUM_NAME)
_IRRADIANCE_PLANE_ENUM = Enum(
    WeatherIrradiancePlane, name=WEATHER_IRRADIANCE_PLANE_ENUM_NAME
)
_TEMPERATURE_TYPE_ENUM = Enum(
    WeatherTemperatureType, name=WEATHER_TEMPERATURE_TYPE_ENUM_NAME
)
_CONFIDENCE_ENUM = Enum(WeatherConfidence, name=WEATHER_CONFIDENCE_ENUM_NAME)
_CALIBRATION_STATUS_ENUM = Enum(
    WeatherCalibrationStatus, name=WEATHER_CALIBRATION_STATUS_ENUM_NAME
)
_APPROVAL_TARGET_TYPE_ENUM = Enum(
    WeatherApprovalTargetType, name=WEATHER_APPROVAL_TARGET_TYPE_ENUM_NAME
)
_APPROVAL_ACTION_ENUM = Enum(
    WeatherApprovalAction, name=WEATHER_APPROVAL_ACTION_ENUM_NAME
)
_DECLARATION_BASIS_ENUM = Enum(
    WeatherDeclarationBasis, name=WEATHER_DECLARATION_BASIS_ENUM_NAME
)
_DECLARATION_STATUS_ENUM = Enum(
    WeatherDeclarationStatus, name=WEATHER_DECLARATION_STATUS_ENUM_NAME
)


# ---------------------------------------------------------------------------
# 1. weather_sources
# ---------------------------------------------------------------------------
class WeatherSource(Base):
    """Catalog of weather source identity + non-secret provider metadata.

    Sources may be global (``company_id``/``site_id`` null), company-scoped, or
    site-scoped. NEVER store API keys/secrets here — only non-secret config and
    licensing notes. Sources are deactivated (``active=False``), not deleted, so
    downstream provenance references remain resolvable.
    """

    __tablename__ = "weather_sources"
    __table_args__ = (
        Index("ix_weather_sources_company", "company_id"),
        Index("ix_weather_sources_site", "site_id"),
        Index("ix_weather_sources_type", "source_type"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=True
    )
    source_type = Column(_SOURCE_TYPE_ENUM, nullable=False)
    display_name = Column(String(255), nullable=False)
    provider_key = Column(String(128), nullable=True)
    is_modeled = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    default_confidence = Column(
        _CONFIDENCE_ENUM,
        nullable=False,
        default=WeatherConfidence.unknown,
        server_default=WeatherConfidence.unknown.value,
    )
    licensing_note = Column(Text, nullable=True)
    active = Column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    created_at = Column(DateTime, nullable=False, server_default=utcnow())
    updated_at = Column(
        DateTime, nullable=False, server_default=utcnow(), onupdate=utcnow()
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherSource(id={self.id}, type={self.source_type}, "
            f"site_id={self.site_id})>"
        )


# ---------------------------------------------------------------------------
# 2. weather_source_profiles
# ---------------------------------------------------------------------------
class WeatherSourceProfile(Base):
    """Effective-dated, per-site source policy.

    Versioned by NEW ROW, never mutated. There is intentionally NO single-active
    constraint: multiple entries may overlap and are ordered by ``priority`` so a
    future resolver can express precedence/fallback. Activation is never
    automatic — a row reaches ``active`` only via an explicit approval action.
    """

    __tablename__ = "weather_source_profiles"
    __table_args__ = (
        Index("ix_weather_source_profiles_site", "site_id"),
        Index("ix_weather_source_profiles_source", "weather_source_id"),
        Index("ix_weather_source_profiles_role", "role"),
        Index("ix_weather_source_profiles_status", "status"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(_PROFILE_ROLE_ENUM, nullable=False)
    weather_source_id = Column(
        Integer, ForeignKey("weather_sources.id", ondelete="CASCADE"), nullable=False
    )
    priority = Column(Integer, nullable=False, default=0, server_default=text("0"))
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    fallback_allowed = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    external_modeled_allowed = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    min_confidence_policy = Column(_CONFIDENCE_ENUM, nullable=True)
    status = Column(
        _PROFILE_STATUS_ENUM,
        nullable=False,
        default=WeatherSourceProfileStatus.draft,
        server_default=WeatherSourceProfileStatus.draft.value,
    )
    approved_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())
    updated_at = Column(
        DateTime, nullable=False, server_default=utcnow(), onupdate=utcnow()
    )

    source = relationship("WeatherSource")

    def __repr__(self) -> str:
        return (
            f"<WeatherSourceProfile(id={self.id}, site_id={self.site_id}, "
            f"role={self.role}, status={self.status})>"
        )


# ---------------------------------------------------------------------------
# 3. weather_observation_batches
# ---------------------------------------------------------------------------
class WeatherObservationBatch(Base):
    """Immutable provenance for an import/pull of weather observations.

    Corrections are made by inserting a NEW batch that supersedes a prior one
    (``superseded_by_batch_id``); existing batches/observations are never mutated
    in place, so weather history is preserved.
    """

    __tablename__ = "weather_observation_batches"
    __table_args__ = (
        Index("ix_weather_observation_batches_site", "site_id"),
        Index("ix_weather_observation_batches_source", "weather_source_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    weather_source_id = Column(
        Integer, ForeignKey("weather_sources.id", ondelete="CASCADE"), nullable=False
    )
    batch_kind = Column(_BATCH_KIND_ENUM, nullable=False)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    row_count = Column(Integer, nullable=True)
    unit_system = Column(String(32), nullable=True)
    timezone_alignment_note = Column(Text, nullable=True)
    source_file_id = Column(
        Integer, ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    imported_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    superseded_by_batch_id = Column(
        Integer,
        ForeignKey("weather_observation_batches.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime, nullable=False, server_default=utcnow())

    observations = relationship(
        "WeatherObservation",
        back_populates="batch",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherObservationBatch(id={self.id}, site_id={self.site_id}, "
            f"kind={self.batch_kind})>"
        )


# ---------------------------------------------------------------------------
# 4. weather_observations
# ---------------------------------------------------------------------------
class WeatherObservation(Base):
    """Non-telemetry weather values (imported, modeled, or manual).

    This table is NOT a replacement for ``telemetry_readings`` — live DAS weather
    stays in telemetry. Rows are append/idempotent by ``dedupe_key`` (a unique
    key encoding site/source/metric/timestamp/plane/temp so re-imports are
    safe). A stored row always carries a real ``value``; a genuinely missing
    reading is represented by the ABSENCE of a row, never a fabricated value.
    ``obs_ts`` uses the existing naive-UTC convention (as telemetry does).
    """

    __tablename__ = "weather_observations"
    __table_args__ = (
        UniqueConstraint("dedupe_key", name="uq_weather_observations_dedupe_key"),
        Index("ix_weather_observations_site", "site_id"),
        Index("ix_weather_observations_batch", "batch_id"),
        Index("ix_weather_observations_source", "weather_source_id"),
        Index(
            "ix_weather_observations_site_metric_ts",
            "site_id",
            "metric",
            "obs_ts",
        ),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    batch_id = Column(
        Integer,
        ForeignKey("weather_observation_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    weather_source_id = Column(
        Integer, ForeignKey("weather_sources.id", ondelete="CASCADE"), nullable=False
    )
    metric = Column(String(64), nullable=False)
    value = Column(Numeric, nullable=False)
    unit = Column(String(32), nullable=True)
    obs_ts = Column(DateTime, nullable=False)
    irradiance_plane = Column(
        _IRRADIANCE_PLANE_ENUM,
        nullable=False,
        default=WeatherIrradiancePlane.unknown,
        server_default=WeatherIrradiancePlane.unknown.value,
    )
    temperature_type = Column(
        _TEMPERATURE_TYPE_ENUM,
        nullable=False,
        default=WeatherTemperatureType.unknown,
        server_default=WeatherTemperatureType.unknown.value,
    )
    is_modeled = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    confidence = Column(
        _CONFIDENCE_ENUM,
        nullable=False,
        default=WeatherConfidence.unknown,
        server_default=WeatherConfidence.unknown.value,
    )
    dedupe_key = Column(String(255), nullable=False)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())

    batch = relationship("WeatherObservationBatch", back_populates="observations")

    def __repr__(self) -> str:
        return (
            f"<WeatherObservation(id={self.id}, site_id={self.site_id}, "
            f"metric={self.metric}, ts={self.obs_ts})>"
        )


# ---------------------------------------------------------------------------
# 5. weather_source_approvals
# ---------------------------------------------------------------------------
class WeatherSourceApproval(Base):
    """Append-only approval ledger for weather profiles and import batches.

    Polymorphic by (``target_type``, ``target_id``) — intentionally no FK so the
    ledger is never cascade-deleted. Rows are immutable (no ``updated_at``).
    """

    __tablename__ = "weather_source_approvals"
    __table_args__ = (
        Index("ix_weather_source_approvals_site", "site_id"),
        Index(
            "ix_weather_source_approvals_target",
            "target_type",
            "target_id",
        ),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    target_type = Column(_APPROVAL_TARGET_TYPE_ENUM, nullable=False)
    target_id = Column(Integer, nullable=False)
    action = Column(_APPROVAL_ACTION_ENUM, nullable=False)
    approved_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime, nullable=True)
    rationale = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())

    def __repr__(self) -> str:
        return (
            f"<WeatherSourceApproval(id={self.id}, target={self.target_type}:"
            f"{self.target_id}, action={self.action})>"
        )


# ---------------------------------------------------------------------------
# 6. weather_device_mappings
# ---------------------------------------------------------------------------
class WeatherDeviceMapping(Base):
    """Declares measurement semantics for weather coming from telemetry devices.

    Existing DAS weather defaults to ``unknown`` semantics until explicitly
    mapped here; we never assume ``irradiance_wm2`` is POA. Effective-dated so a
    re-calibration can change semantics without rewriting history.
    """

    __tablename__ = "weather_device_mappings"
    __table_args__ = (
        Index("ix_weather_device_mappings_site", "site_id"),
        Index("ix_weather_device_mappings_device", "device_id"),
        Index("ix_weather_device_mappings_source", "weather_source_id"),
        # WS.1: current-declaration resolution per (device, metric) by status.
        Index(
            "ix_weather_device_mappings_declaration",
            "device_id",
            "metric",
            "declaration_status",
        ),
        Index("ix_weather_device_mappings_decl_status", "declaration_status"),
        # WS.2: single-active enforcement per lineage at the DB level. A governed
        # row may be ACTIVE for at most one (site, device|external_device, metric)
        # lineage at a time. Partial so legacy (NULL-status), draft, and superseded
        # rows are never constrained; split on ``device_id`` because the lineage is
        # keyed by ``external_device_id`` when ``device_id`` is NULL.
        Index(
            "uq_weather_device_mappings_active_device",
            "site_id",
            "device_id",
            "metric",
            unique=True,
            postgresql_where=text(
                "declaration_status = 'active' AND device_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_weather_device_mappings_active_external",
            "site_id",
            "external_device_id",
            "metric",
            unique=True,
            postgresql_where=text(
                "declaration_status = 'active' AND device_id IS NULL"
            ),
        ),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    external_device_id = Column(String(255), nullable=True)
    weather_source_id = Column(
        Integer, ForeignKey("weather_sources.id", ondelete="SET NULL"), nullable=True
    )
    metric = Column(String(64), nullable=False)
    provider_key = Column(String(128), nullable=True)
    irradiance_plane = Column(
        _IRRADIANCE_PLANE_ENUM,
        nullable=False,
        default=WeatherIrradiancePlane.unknown,
        server_default=WeatherIrradiancePlane.unknown.value,
    )
    temperature_type = Column(
        _TEMPERATURE_TYPE_ENUM,
        nullable=False,
        default=WeatherTemperatureType.unknown,
        server_default=WeatherTemperatureType.unknown.value,
    )
    calibration_status = Column(
        _CALIBRATION_STATUS_ENUM,
        nullable=False,
        default=WeatherCalibrationStatus.unknown,
        server_default=WeatherCalibrationStatus.unknown.value,
    )
    calibrated_at = Column(DateTime, nullable=True)
    calibration_reference = Column(String(255), nullable=True)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)

    # -- WS.1 governance layer (additive, NULLable) --------------------------
    # A NULL ``declaration_status`` marks a legacy/ungoverned row that predates
    # this governance layer; such rows are exempt from the append-only guard.
    declaration_status = Column(_DECLARATION_STATUS_ENUM, nullable=True)
    declaration_basis = Column(_DECLARATION_BASIS_ENUM, nullable=True)
    # Evidence backing the declaration (cross-tenant validated in the service).
    source_document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    source_file_id = Column(
        Integer, ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    reviewer_note = Column(Text, nullable=True)
    sensor_role = Column(String(128), nullable=True)
    sensor_model = Column(String(255), nullable=True)
    provider_metadata_json = Column(JSONB, nullable=True)
    # Snapshot of the upstream device fingerprint at declaration time; WS.3
    # compares it to the live fingerprint to flag stale declarations.
    upstream_fingerprint_json = Column(JSONB, nullable=True)
    # Lifecycle (set-once columns enforced by the append-only guard).
    declared_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    declared_at = Column(DateTime, nullable=True)
    activated_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    activated_at = Column(DateTime, nullable=True)
    supersedes_mapping_id = Column(
        Integer,
        ForeignKey("weather_device_mappings.id", ondelete="SET NULL"),
        nullable=True,
    )
    superseded_by_mapping_id = Column(
        Integer,
        ForeignKey("weather_device_mappings.id", ondelete="SET NULL"),
        nullable=True,
    )
    # ``needs_re_review`` is a monotonic flag (false->true only), NOT a status.
    needs_re_review = Column(Boolean, nullable=True)
    re_review_reason = Column(Text, nullable=True)
    # Audit-only snapshot of the eligibility verdict captured at activation.
    eligibility_snapshot_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())
    updated_at = Column(
        DateTime, nullable=False, server_default=utcnow(), onupdate=utcnow()
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherDeviceMapping(id={self.id}, site_id={self.site_id}, "
            f"metric={self.metric}, plane={self.irradiance_plane}, "
            f"status={self.declaration_status})>"
        )


# ---------------------------------------------------------------------------
# 7. expected_weather_provenance  (DEFINED in W0; NOT written by runtime)
# ---------------------------------------------------------------------------
class ExpectedWeatherProvenance(Base):
    """Forward placeholder: which weather source drove an expected computation.

    Defined now because it is low-risk and additive, but NOTHING writes to it in
    W0 — ``expected_service`` is unchanged. A future WeatherResolver (W1+) will
    populate it so O&M and reporting can disclose what drove each expected line.
    """

    __tablename__ = "expected_weather_provenance"
    __table_args__ = (
        Index("ix_expected_weather_provenance_site", "site_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    weather_source_id = Column(
        Integer, ForeignKey("weather_sources.id", ondelete="SET NULL"), nullable=True
    )
    profile_id = Column(
        Integer,
        ForeignKey("weather_source_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    computed_at = Column(DateTime, nullable=True)
    window_start = Column(DateTime, nullable=True)
    window_end = Column(DateTime, nullable=True)
    bucket_size = Column(String(16), nullable=True)
    is_modeled = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    confidence = Column(
        _CONFIDENCE_ENUM,
        nullable=False,
        default=WeatherConfidence.unknown,
        server_default=WeatherConfidence.unknown.value,
    )
    coverage_pct = Column(Numeric, nullable=True)
    missing_input_buckets = Column(Integer, nullable=True)
    summary_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())

    def __repr__(self) -> str:
        return (
            f"<ExpectedWeatherProvenance(id={self.id}, site_id={self.site_id}, "
            f"source_id={self.weather_source_id})>"
        )


# ---------------------------------------------------------------------------
# WS.1 append-only ORM guard (defense in depth; the DB trigger is authoritative)
# ---------------------------------------------------------------------------
@event.listens_for(WeatherDeviceMapping, "before_update", propagate=True)
def _enforce_weather_declaration_append_only(mapper, connection, target):  # noqa: U100
    """Reject illegal in-place edits to a *governed* weather declaration.

    Mirrors the ``enforce_weather_declaration_append_only`` DB trigger so app code
    fails fast. Legacy/ungoverned rows (``declaration_status`` NULL) are exempt.
    Builds null-safe old/new value maps from attribute history and delegates the
    decision to the pure validator in ``app.db.weather_declaration_guard``.
    """
    old: dict = {}
    new: dict = {}
    for attr in mapper.column_attrs:
        key = attr.key
        new_val = getattr(target, key)
        history = get_history(target, key)
        if history.deleted:
            old_val = history.deleted[0]
        elif history.unchanged:
            old_val = history.unchanged[0]
        else:
            # No recorded prior value (e.g. unchanged & not loaded) -> treat as
            # equal to the new value so it is not flagged as a change.
            old_val = new_val
        old[key] = old_val
        new[key] = new_val
    assert_governed_update_allowed(old, new)
