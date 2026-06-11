"""Expected-performance baselines: versioned approved baselines + curve points.

Revision ID: ff28_telemetry_expected_baselines
Revises: ff27_site_timezone
Create Date: 2026-06-11

Background
----------
Phase P3.1 of the Expected Performance Baseline sprint. Adds the durable schema
the native weather-adjusted expected calculation (Phase P3.2) reads from,
replacing the legacy BigQuery ``site_characteristics`` / ``device_characteristics``
inputs:

* ``telemetry_expected_baselines`` — one row per versioned, human-approved set
  of expected assumptions for a site. ``baseline_type`` distinguishes the static
  ``design_estimate`` (PVsyst forecast) from the operational
  ``weather_adjusted_model`` (the live expected line). Physics assumptions are
  snapshot as typed columns at creation (losses + PTO copied from
  ``site_additional_fields`` with sign normalization) so an approved baseline is
  immutable and fully reproducible. Percent columns are stored AS PERCENT.
* ``telemetry_expected_baseline_points`` — stored expected curve points
  (primarily a ``design_estimate`` monthly/annual curve; the weather-adjusted
  model is computed on read, not stored here).

Four new Postgres enum types are created
(``telemetry_baseline_type_enum``, ``telemetry_baseline_status_enum``,
``telemetry_baseline_source_enum``, ``telemetry_baseline_granularity_enum``).

Approval contract
-----------------
At most one baseline per site per ``baseline_type`` may be ``active`` at once,
enforced by the partial unique index
``uq_telemetry_expected_baseline_active`` (``WHERE status = 'active'``).
Superseded baselines remain in the table for audit
(``active_from`` / ``active_to`` / ``supersedes_baseline_id``).

This migration is ADDITIVE ONLY. It does not touch the ``sites`` table, the
``site_additional_fields`` table, or any existing telemetry table/enum.

Rollback
--------
``downgrade()`` drops the two tables (child first) and the four new enum types.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff28_telemetry_expected_baselines"
down_revision = "ff27_site_timezone"
branch_labels = None
depends_on = None


BASELINE_TYPE_ENUM_NAME = "telemetry_baseline_type_enum"
BASELINE_STATUS_ENUM_NAME = "telemetry_baseline_status_enum"
BASELINE_SOURCE_ENUM_NAME = "telemetry_baseline_source_enum"
BASELINE_GRANULARITY_ENUM_NAME = "telemetry_baseline_granularity_enum"

BASELINE_TYPES = ("design_estimate", "weather_adjusted_model", "imported_8760", "manual")
BASELINE_STATUSES = (
    "draft",
    "in_review",
    "approved",
    "active",
    "superseded",
    "rejected",
)
BASELINE_SOURCES = (
    "pvsyst",
    "design_document",
    "diligence_ai_parse",
    "manual_entry",
    "imported_8760",
    "legacy_formula",
)
BASELINE_GRANULARITIES = ("hourly", "daily", "monthly", "annual", "interval")


def upgrade() -> None:
    bind = op.get_bind()

    baseline_type_enum = postgresql.ENUM(
        *BASELINE_TYPES, name=BASELINE_TYPE_ENUM_NAME, create_type=False
    )
    baseline_status_enum = postgresql.ENUM(
        *BASELINE_STATUSES, name=BASELINE_STATUS_ENUM_NAME, create_type=False
    )
    baseline_source_enum = postgresql.ENUM(
        *BASELINE_SOURCES, name=BASELINE_SOURCE_ENUM_NAME, create_type=False
    )
    baseline_granularity_enum = postgresql.ENUM(
        *BASELINE_GRANULARITIES, name=BASELINE_GRANULARITY_ENUM_NAME, create_type=False
    )
    baseline_type_enum.create(bind, checkfirst=True)
    baseline_status_enum.create(bind, checkfirst=True)
    baseline_source_enum.create(bind, checkfirst=True)
    baseline_granularity_enum.create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # telemetry_expected_baselines
    # ------------------------------------------------------------------
    op.create_table(
        "telemetry_expected_baselines",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("baseline_name", sa.String(255), nullable=False),
        sa.Column(
            "baseline_type",
            postgresql.ENUM(
                *BASELINE_TYPES, name=BASELINE_TYPE_ENUM_NAME, create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                *BASELINE_STATUSES, name=BASELINE_STATUS_ENUM_NAME, create_type=False
            ),
            nullable=False,
            server_default=sa.text(f"'draft'::{BASELINE_STATUS_ENUM_NAME}"),
        ),
        sa.Column(
            "source_type",
            postgresql.ENUM(
                *BASELINE_SOURCES, name=BASELINE_SOURCE_ENUM_NAME, create_type=False
            ),
            nullable=True,
        ),
        sa.Column(
            "source_document_id",
            sa.Integer,
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_project_fact_id",
            sa.Integer,
            sa.ForeignKey("project_facts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("timezone", sa.String(64), nullable=True),
        sa.Column("system_size_ac_kw", sa.Numeric, nullable=True),
        sa.Column("system_size_dc_kw", sa.Numeric, nullable=True),
        sa.Column("degradation_rate", sa.Numeric, nullable=True),
        # Typed physics assumptions (immutable calc snapshot).
        sa.Column("module_wattage", sa.Numeric, nullable=True),
        sa.Column("module_quantity", sa.Numeric, nullable=True),
        sa.Column("inverter_wattage", sa.Numeric, nullable=True),
        sa.Column("inverter_quantity", sa.Numeric, nullable=True),
        sa.Column("thermal_coefficient_pct", sa.Numeric, nullable=True),
        sa.Column("power_tolerance_min_pct", sa.Numeric, nullable=True),
        sa.Column("year_1_degradation_pct", sa.Numeric, nullable=True),
        sa.Column("annual_degradation_pct", sa.Numeric, nullable=True),
        sa.Column("cec_efficiency_pct", sa.Numeric, nullable=True),
        sa.Column("soiling_factor", sa.Numeric, nullable=True),
        sa.Column("dc_loss_pct", sa.Numeric, nullable=True),
        sa.Column("ac_loss_pct", sa.Numeric, nullable=True),
        sa.Column("medium_voltage_loss_pct", sa.Numeric, nullable=True),
        sa.Column("mv_line_loss_pct", sa.Numeric, nullable=True),
        sa.Column("pto_date", sa.Date, nullable=True),
        sa.Column("loss_assumptions_json", postgresql.JSONB, nullable=True),
        sa.Column("model_parameters_json", postgresql.JSONB, nullable=True),
        sa.Column("ai_confidence_json", postgresql.JSONB, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column(
            "reviewed_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column(
            "approved_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("active_from", sa.DateTime, nullable=True),
        sa.Column("active_to", sa.DateTime, nullable=True),
        sa.Column(
            "supersedes_baseline_id",
            sa.Integer,
            sa.ForeignKey("telemetry_expected_baselines.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_telemetry_expected_baseline_active",
        "telemetry_expected_baselines",
        ["site_id", "baseline_type"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_telemetry_expected_baselines_site",
        "telemetry_expected_baselines",
        ["site_id"],
    )
    op.create_index(
        "ix_telemetry_expected_baselines_company",
        "telemetry_expected_baselines",
        ["company_id"],
    )
    op.create_index(
        "ix_telemetry_expected_baselines_status",
        "telemetry_expected_baselines",
        ["status"],
    )

    # ------------------------------------------------------------------
    # telemetry_expected_baseline_points
    # ------------------------------------------------------------------
    op.create_table(
        "telemetry_expected_baseline_points",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "baseline_id",
            sa.Integer,
            sa.ForeignKey("telemetry_expected_baselines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Integer,
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("point_ts", sa.DateTime, nullable=False),
        sa.Column("interval_minutes", sa.Integer, nullable=True),
        sa.Column("expected_power_kw", sa.Numeric, nullable=True),
        sa.Column("expected_energy_kwh", sa.Numeric, nullable=True),
        sa.Column("irradiance_wm2", sa.Numeric, nullable=True),
        sa.Column("cell_temperature_f", sa.Numeric, nullable=True),
        sa.Column("ambient_temperature_f", sa.Numeric, nullable=True),
        sa.Column(
            "source_granularity",
            postgresql.ENUM(
                *BASELINE_GRANULARITIES,
                name=BASELINE_GRANULARITY_ENUM_NAME,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("calculation_method", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "baseline_id",
            "source_granularity",
            "point_ts",
            name="uq_telemetry_expected_baseline_point",
        ),
    )
    op.create_index(
        "ix_telemetry_expected_baseline_points_baseline",
        "telemetry_expected_baseline_points",
        ["baseline_id"],
    )
    op.create_index(
        "ix_telemetry_expected_baseline_points_site",
        "telemetry_expected_baseline_points",
        ["site_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        "ix_telemetry_expected_baseline_points_site",
        table_name="telemetry_expected_baseline_points",
    )
    op.drop_index(
        "ix_telemetry_expected_baseline_points_baseline",
        table_name="telemetry_expected_baseline_points",
    )
    op.drop_table("telemetry_expected_baseline_points")

    op.drop_index(
        "ix_telemetry_expected_baselines_status",
        table_name="telemetry_expected_baselines",
    )
    op.drop_index(
        "ix_telemetry_expected_baselines_company",
        table_name="telemetry_expected_baselines",
    )
    op.drop_index(
        "ix_telemetry_expected_baselines_site",
        table_name="telemetry_expected_baselines",
    )
    op.drop_index(
        "uq_telemetry_expected_baseline_active",
        table_name="telemetry_expected_baselines",
    )
    op.drop_table("telemetry_expected_baselines")

    postgresql.ENUM(name=BASELINE_GRANULARITY_ENUM_NAME, create_type=False).drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(name=BASELINE_SOURCE_ENUM_NAME, create_type=False).drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(name=BASELINE_STATUS_ENUM_NAME, create_type=False).drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(name=BASELINE_TYPE_ENUM_NAME, create_type=False).drop(
        bind, checkfirst=True
    )
