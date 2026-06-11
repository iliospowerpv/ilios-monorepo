"""V2 expected-performance baseline models (Phase P3.1).

These tables store the *approved* assumptions that drive the native
weather-adjusted expected calculation (Phase P3.2), replacing the legacy
BigQuery ``site_characteristics`` / ``device_characteristics`` inputs. Nothing
here reads BigQuery, Firestore, or the legacy rea-telemetry pipeline.

Two distinct notions of "expected" are modelled by ``baseline_type`` and must
never be conflated (see ``.agents/memory/telemetry-expected-baseline-design.md``):

* ``design_estimate`` — the static PVsyst/design contract forecast (annual /
  monthly). Seeds assumptions; it is NOT the live operational expected line.
* ``weather_adjusted_model`` — the operational expected line computed per
  rollup bucket from the approved physics assumptions PLUS measured V2
  irradiance and cell temperature. This is what the legacy BigQuery physics
  model produced and what P3.2 rebuilds natively.

Approval / provenance mirrors ``project_facts`` + ``assumptions_promotions``:
an AI-parsed baseline is created in ``draft`` and must be human ``approved``
before it can be ``activate``-d. Exactly one baseline per site per
``baseline_type`` may be ``active`` (enforced by a partial unique index);
superseded baselines remain in the table for audit.

Physics assumptions are SNAPSHOT onto the baseline header as typed columns at
creation time (losses + PTO are copied from ``site_additional_fields`` with
sign normalization). The calc service reads ONLY the immutable snapshot, never
the live ``site_additional_fields`` row, so an approved baseline is fully
reproducible. Percent-valued columns are stored AS PERCENT (e.g. ``-0.45`` for
a -0.45 %/°C thermal coefficient, ``98.5`` for 98.5 % efficiency); the calc
divides by 100 exactly once.
"""
import enum

from sqlalchemy import (
    Column,
    Date,
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class TelemetryBaselineType(str, enum.Enum):
    """What kind of expectation a baseline represents.

    Only ``weather_adjusted_model`` drives the live actual-vs-expected calc in
    P3.2; the others are carried for forward compatibility / provenance and the
    spec's documented domain.
    """

    design_estimate = "design_estimate"
    weather_adjusted_model = "weather_adjusted_model"
    imported_8760 = "imported_8760"
    manual = "manual"


class TelemetryBaselineStatus(str, enum.Enum):
    """Approval lifecycle. AI parses land in ``draft``; only ``approved`` may be
    activated; activating supersedes the prior ``active`` row."""

    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    active = "active"
    superseded = "superseded"
    rejected = "rejected"


class TelemetryBaselineSource(str, enum.Enum):
    """Where the baseline assumptions came from (provenance only)."""

    pvsyst = "pvsyst"
    design_document = "design_document"
    diligence_ai_parse = "diligence_ai_parse"
    manual_entry = "manual_entry"
    imported_8760 = "imported_8760"
    legacy_formula = "legacy_formula"


class TelemetryBaselineGranularity(str, enum.Enum):
    """Granularity of a stored expected curve point."""

    hourly = "hourly"
    daily = "daily"
    monthly = "monthly"
    annual = "annual"
    interval = "interval"


BASELINE_TYPE_ENUM_NAME = "telemetry_baseline_type_enum"
BASELINE_STATUS_ENUM_NAME = "telemetry_baseline_status_enum"
BASELINE_SOURCE_ENUM_NAME = "telemetry_baseline_source_enum"
BASELINE_GRANULARITY_ENUM_NAME = "telemetry_baseline_granularity_enum"


class TelemetryExpectedBaseline(Base):
    """Versioned, human-approved expected baseline header for one site.

    The typed ``*_pct`` / nameplate columns are the immutable snapshot the calc
    service consumes. ``model_parameters_json`` / ``loss_assumptions_json`` /
    ``ai_confidence_json`` carry any extra (e.g. AI extraction) detail without
    bloating the typed surface.
    """

    __tablename__ = "telemetry_expected_baselines"
    __table_args__ = (
        # Exactly one ACTIVE baseline per site per type at a time. Historical
        # periods live in superseded rows (active_from / active_to).
        Index(
            "uq_telemetry_expected_baseline_active",
            "site_id",
            "baseline_type",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
        Index("ix_telemetry_expected_baselines_site", "site_id"),
        Index("ix_telemetry_expected_baselines_company", "company_id"),
        Index("ix_telemetry_expected_baselines_status", "status"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(
        Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    # A Site IS the project in this domain; no separate project_id column.
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )

    baseline_name = Column(String(255), nullable=False)
    baseline_type = Column(
        Enum(TelemetryBaselineType, name=BASELINE_TYPE_ENUM_NAME),
        nullable=False,
    )
    status = Column(
        Enum(TelemetryBaselineStatus, name=BASELINE_STATUS_ENUM_NAME),
        nullable=False,
        default=TelemetryBaselineStatus.draft,
        server_default=TelemetryBaselineStatus.draft.value,
    )
    source_type = Column(
        Enum(TelemetryBaselineSource, name=BASELINE_SOURCE_ENUM_NAME),
        nullable=True,
    )

    # Provenance (mirrors project_facts) — all nullable, SET NULL on delete.
    source_document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    source_project_fact_id = Column(
        Integer, ForeignKey("project_facts.id", ondelete="SET NULL"), nullable=True
    )

    # Snapshot of the site's IANA timezone at creation (used for site-local age).
    timezone = Column(String(64), nullable=True)

    # Spec summary fields.
    system_size_ac_kw = Column(Numeric, nullable=True)
    system_size_dc_kw = Column(Numeric, nullable=True)
    degradation_rate = Column(Numeric, nullable=True)

    # ---- Typed physics assumptions (the immutable calc snapshot) ----
    module_wattage = Column(Numeric, nullable=True)
    module_quantity = Column(Numeric, nullable=True)
    inverter_wattage = Column(Numeric, nullable=True)
    inverter_quantity = Column(Numeric, nullable=True)
    # Stored AS PERCENT (calc divides by 100 once).
    thermal_coefficient_pct = Column(Numeric, nullable=True)
    power_tolerance_min_pct = Column(Numeric, nullable=True)
    year_1_degradation_pct = Column(Numeric, nullable=True)
    annual_degradation_pct = Column(Numeric, nullable=True)
    cec_efficiency_pct = Column(Numeric, nullable=True)
    soiling_factor = Column(Numeric, nullable=True)  # fraction, default 1.0
    # Loss percentages — snapshot from site_additional_fields, sign-normalized
    # to positive percent at creation (the formula subtracts a positive %/100).
    dc_loss_pct = Column(Numeric, nullable=True)
    ac_loss_pct = Column(Numeric, nullable=True)
    medium_voltage_loss_pct = Column(Numeric, nullable=True)
    mv_line_loss_pct = Column(Numeric, nullable=True)
    pto_date = Column(Date, nullable=True)

    # Free-form extras / AI detail.
    loss_assumptions_json = Column(JSONB, nullable=True)
    model_parameters_json = Column(JSONB, nullable=True)
    ai_confidence_json = Column(JSONB, nullable=True)

    version = Column(Integer, nullable=False, default=1, server_default="1")

    reviewed_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at = Column(DateTime, nullable=True)
    approved_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at = Column(DateTime, nullable=True)
    active_from = Column(DateTime, nullable=True)
    active_to = Column(DateTime, nullable=True)
    supersedes_baseline_id = Column(
        Integer,
        ForeignKey("telemetry_expected_baselines.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())
    updated_at = Column(
        DateTime, nullable=False, server_default=utcnow(), onupdate=utcnow()
    )

    points = relationship(
        "TelemetryExpectedBaselinePoint",
        back_populates="baseline",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    supersedes = relationship(
        "TelemetryExpectedBaseline", remote_side=[id], foreign_keys=[supersedes_baseline_id]
    )

    def __repr__(self) -> str:
        return (
            f"<TelemetryExpectedBaseline(id={self.id}, site_id={self.site_id}, "
            f"type={self.baseline_type}, status={self.status})>"
        )


class TelemetryExpectedBaselinePoint(Base):
    """A single point of a stored expected curve for a baseline.

    Primarily used to persist a ``design_estimate`` monthly/annual curve (the
    weather-adjusted model is computed on read, not stored here). Wide format
    per spec: one row per ``point_ts`` carrying the available value columns.
    Site-level only for now (``device_id`` is reserved for future per-device
    curves); the unique constraint keys on the site-level grain.
    """

    __tablename__ = "telemetry_expected_baseline_points"
    __table_args__ = (
        UniqueConstraint(
            "baseline_id",
            "source_granularity",
            "point_ts",
            name="uq_telemetry_expected_baseline_point",
        ),
        Index("ix_telemetry_expected_baseline_points_baseline", "baseline_id"),
        Index("ix_telemetry_expected_baseline_points_site", "site_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    baseline_id = Column(
        Integer,
        ForeignKey("telemetry_expected_baselines.id", ondelete="CASCADE"),
        nullable=False,
    )
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )
    device_id = Column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    point_ts = Column(DateTime, nullable=False)
    interval_minutes = Column(Integer, nullable=True)
    expected_power_kw = Column(Numeric, nullable=True)
    expected_energy_kwh = Column(Numeric, nullable=True)
    irradiance_wm2 = Column(Numeric, nullable=True)
    cell_temperature_f = Column(Numeric, nullable=True)
    ambient_temperature_f = Column(Numeric, nullable=True)
    source_granularity = Column(
        Enum(TelemetryBaselineGranularity, name=BASELINE_GRANULARITY_ENUM_NAME),
        nullable=False,
    )
    calculation_method = Column(String(64), nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())

    baseline = relationship("TelemetryExpectedBaseline", back_populates="points")

    def __repr__(self) -> str:
        return (
            f"<TelemetryExpectedBaselinePoint(id={self.id}, "
            f"baseline_id={self.baseline_id}, ts={self.point_ts})>"
        )
