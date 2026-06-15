"""Weather Data Architecture W0 — native weather provenance foundation.

Revision ID: ff32_weather_provenance_foundation
Revises: ff31_dd_v2_pvsyst_specialized_schema_v2
Create Date: 2026-06-15

Background
----------
Adds an auditable weather domain that COEXISTS beside the V2 telemetry stack
(``telemetry_readings`` / rollups are untouched). See ``app/models/weather.py``
for the full contract. Seven additive tables + ten Postgres enum types:

* ``weather_sources`` — source identity + non-secret provider metadata.
* ``weather_source_profiles`` — effective-dated, per-site source policy,
  versioned by new row, no single-active constraint (overlap + ``priority`` are
  intentional so a future resolver can express precedence/fallback).
* ``weather_observation_batches`` — immutable import/pull provenance.
* ``weather_observations`` — non-telemetry weather values, append/idempotent on a
  ``dedupe_key`` unique constraint (NOT a replacement for ``telemetry_readings``).
* ``weather_source_approvals`` — append-only, polymorphic approval ledger.
* ``weather_device_mappings`` — measurement semantics (irradiance plane /
  temperature type / calibration) for telemetry weather; defaults ``unknown`` so
  unmapped DAS weather is never assumed to be POA/cell.
* ``expected_weather_provenance`` — forward placeholder; NOTHING writes to it in
  W0 (``expected_service`` is unchanged).

This migration is ADDITIVE ONLY. It does not touch ``sites``, telemetry tables,
project_facts, or any existing enum. No external provider, secret, BigQuery, or
Firestore concern is introduced.

Rollback
--------
``downgrade()`` drops the seven tables (children first) then the ten enum types.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff32_weather_provenance_foundation"
down_revision = "ff31_dd_v2_pvsyst_specialized_schema_v2"
branch_labels = None
depends_on = None


# Enum type names (kept in lockstep with app/models/weather.py).
SOURCE_TYPE_ENUM_NAME = "weather_source_type_enum"
PROFILE_ROLE_ENUM_NAME = "weather_source_profile_role_enum"
PROFILE_STATUS_ENUM_NAME = "weather_source_profile_status_enum"
BATCH_KIND_ENUM_NAME = "weather_observation_batch_kind_enum"
IRRADIANCE_PLANE_ENUM_NAME = "weather_irradiance_plane_enum"
TEMPERATURE_TYPE_ENUM_NAME = "weather_temperature_type_enum"
CONFIDENCE_ENUM_NAME = "weather_confidence_enum"
CALIBRATION_STATUS_ENUM_NAME = "weather_calibration_status_enum"
APPROVAL_TARGET_TYPE_ENUM_NAME = "weather_approval_target_type_enum"
APPROVAL_ACTION_ENUM_NAME = "weather_approval_action_enum"

SOURCE_TYPES = (
    "on_site_calibrated_sensor",
    "on_site_weather_station",
    "das_provider_stream",
    "external_modeled_provider",
    "imported_historical_provider_file",
    "imported_weather_station_file",
    "pvsyst_design_weather",
    "manual_approved_weather_assumption",
    "unavailable",
)
PROFILE_ROLES = ("live", "historical", "design", "fallback")
PROFILE_STATUSES = (
    "draft",
    "in_review",
    "approved",
    "active",
    "superseded",
    "rejected",
)
BATCH_KINDS = ("file_import", "provider_pull", "manual", "telemetry_backfill")
IRRADIANCE_PLANES = ("poa", "ghi", "dni", "dhi", "unknown")
TEMPERATURE_TYPES = ("cell", "module", "ambient", "modeled_cell", "unknown")
CONFIDENCES = ("high", "medium", "low", "unknown")
CALIBRATION_STATUSES = ("calibrated", "uncalibrated", "expired", "unknown")
APPROVAL_TARGET_TYPES = ("profile", "batch")
APPROVAL_ACTIONS = ("approve", "reject", "revoke", "supersede")


def _enum(name, values):
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # Enum types (created once; columns reference them with create_type=False)
    # ------------------------------------------------------------------
    enum_defs = (
        (SOURCE_TYPE_ENUM_NAME, SOURCE_TYPES),
        (PROFILE_ROLE_ENUM_NAME, PROFILE_ROLES),
        (PROFILE_STATUS_ENUM_NAME, PROFILE_STATUSES),
        (BATCH_KIND_ENUM_NAME, BATCH_KINDS),
        (IRRADIANCE_PLANE_ENUM_NAME, IRRADIANCE_PLANES),
        (TEMPERATURE_TYPE_ENUM_NAME, TEMPERATURE_TYPES),
        (CONFIDENCE_ENUM_NAME, CONFIDENCES),
        (CALIBRATION_STATUS_ENUM_NAME, CALIBRATION_STATUSES),
        (APPROVAL_TARGET_TYPE_ENUM_NAME, APPROVAL_TARGET_TYPES),
        (APPROVAL_ACTION_ENUM_NAME, APPROVAL_ACTIONS),
    )
    for name, values in enum_defs:
        _enum(name, values).create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # 1. weather_sources
    # ------------------------------------------------------------------
    op.create_table(
        "weather_sources",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("source_type", _enum(SOURCE_TYPE_ENUM_NAME, SOURCE_TYPES), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("provider_key", sa.String(128), nullable=True),
        sa.Column(
            "is_modeled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "default_confidence",
            _enum(CONFIDENCE_ENUM_NAME, CONFIDENCES),
            nullable=False,
            server_default=sa.text(f"'unknown'::{CONFIDENCE_ENUM_NAME}"),
        ),
        sa.Column("licensing_note", sa.Text, nullable=True),
        sa.Column(
            "active", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_weather_sources_company", "weather_sources", ["company_id"])
    op.create_index("ix_weather_sources_site", "weather_sources", ["site_id"])
    op.create_index("ix_weather_sources_type", "weather_sources", ["source_type"])

    # ------------------------------------------------------------------
    # 2. weather_source_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "weather_source_profiles",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", _enum(PROFILE_ROLE_ENUM_NAME, PROFILE_ROLES), nullable=False),
        sa.Column(
            "weather_source_id",
            sa.Integer,
            sa.ForeignKey("weather_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("effective_from", sa.DateTime, nullable=True),
        sa.Column("effective_to", sa.DateTime, nullable=True),
        sa.Column(
            "fallback_allowed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "external_modeled_allowed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "min_confidence_policy",
            _enum(CONFIDENCE_ENUM_NAME, CONFIDENCES),
            nullable=True,
        ),
        sa.Column(
            "status",
            _enum(PROFILE_STATUS_ENUM_NAME, PROFILE_STATUSES),
            nullable=False,
            server_default=sa.text(f"'draft'::{PROFILE_STATUS_ENUM_NAME}"),
        ),
        sa.Column(
            "approved_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_weather_source_profiles_site", "weather_source_profiles", ["site_id"]
    )
    op.create_index(
        "ix_weather_source_profiles_source",
        "weather_source_profiles",
        ["weather_source_id"],
    )
    op.create_index(
        "ix_weather_source_profiles_role", "weather_source_profiles", ["role"]
    )
    op.create_index(
        "ix_weather_source_profiles_status", "weather_source_profiles", ["status"]
    )

    # ------------------------------------------------------------------
    # 3. weather_observation_batches
    # ------------------------------------------------------------------
    op.create_table(
        "weather_observation_batches",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "weather_source_id",
            sa.Integer,
            sa.ForeignKey("weather_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "batch_kind", _enum(BATCH_KIND_ENUM_NAME, BATCH_KINDS), nullable=False
        ),
        sa.Column("period_start", sa.DateTime, nullable=True),
        sa.Column("period_end", sa.DateTime, nullable=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("unit_system", sa.String(32), nullable=True),
        sa.Column("timezone_alignment_note", sa.Text, nullable=True),
        sa.Column(
            "source_file_id",
            sa.Integer,
            sa.ForeignKey("files.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "imported_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "superseded_by_batch_id",
            sa.Integer,
            sa.ForeignKey("weather_observation_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_weather_observation_batches_site",
        "weather_observation_batches",
        ["site_id"],
    )
    op.create_index(
        "ix_weather_observation_batches_source",
        "weather_observation_batches",
        ["weather_source_id"],
    )

    # ------------------------------------------------------------------
    # 4. weather_observations
    # ------------------------------------------------------------------
    op.create_table(
        "weather_observations",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "batch_id",
            sa.Integer,
            sa.ForeignKey("weather_observation_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "weather_source_id",
            sa.Integer,
            sa.ForeignKey("weather_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("value", sa.Numeric, nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("obs_ts", sa.DateTime, nullable=False),
        sa.Column(
            "irradiance_plane",
            _enum(IRRADIANCE_PLANE_ENUM_NAME, IRRADIANCE_PLANES),
            nullable=False,
            server_default=sa.text(f"'unknown'::{IRRADIANCE_PLANE_ENUM_NAME}"),
        ),
        sa.Column(
            "temperature_type",
            _enum(TEMPERATURE_TYPE_ENUM_NAME, TEMPERATURE_TYPES),
            nullable=False,
            server_default=sa.text(f"'unknown'::{TEMPERATURE_TYPE_ENUM_NAME}"),
        ),
        sa.Column(
            "is_modeled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "confidence",
            _enum(CONFIDENCE_ENUM_NAME, CONFIDENCES),
            nullable=False,
            server_default=sa.text(f"'unknown'::{CONFIDENCE_ENUM_NAME}"),
        ),
        sa.Column("dedupe_key", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("dedupe_key", name="uq_weather_observations_dedupe_key"),
    )
    op.create_index("ix_weather_observations_site", "weather_observations", ["site_id"])
    op.create_index(
        "ix_weather_observations_batch", "weather_observations", ["batch_id"]
    )
    op.create_index(
        "ix_weather_observations_source",
        "weather_observations",
        ["weather_source_id"],
    )
    op.create_index(
        "ix_weather_observations_site_metric_ts",
        "weather_observations",
        ["site_id", "metric", "obs_ts"],
    )

    # ------------------------------------------------------------------
    # 5. weather_source_approvals  (append-only, polymorphic target)
    # ------------------------------------------------------------------
    op.create_table(
        "weather_source_approvals",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_type",
            _enum(APPROVAL_TARGET_TYPE_ENUM_NAME, APPROVAL_TARGET_TYPES),
            nullable=False,
        ),
        sa.Column("target_id", sa.Integer, nullable=False),
        sa.Column(
            "action", _enum(APPROVAL_ACTION_ENUM_NAME, APPROVAL_ACTIONS), nullable=False
        ),
        sa.Column(
            "approved_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_weather_source_approvals_site", "weather_source_approvals", ["site_id"]
    )
    op.create_index(
        "ix_weather_source_approvals_target",
        "weather_source_approvals",
        ["target_type", "target_id"],
    )

    # ------------------------------------------------------------------
    # 6. weather_device_mappings
    # ------------------------------------------------------------------
    op.create_table(
        "weather_device_mappings",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
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
        sa.Column("external_device_id", sa.String(255), nullable=True),
        sa.Column(
            "weather_source_id",
            sa.Integer,
            sa.ForeignKey("weather_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metric", sa.String(64), nullable=False),
        sa.Column("provider_key", sa.String(128), nullable=True),
        sa.Column(
            "irradiance_plane",
            _enum(IRRADIANCE_PLANE_ENUM_NAME, IRRADIANCE_PLANES),
            nullable=False,
            server_default=sa.text(f"'unknown'::{IRRADIANCE_PLANE_ENUM_NAME}"),
        ),
        sa.Column(
            "temperature_type",
            _enum(TEMPERATURE_TYPE_ENUM_NAME, TEMPERATURE_TYPES),
            nullable=False,
            server_default=sa.text(f"'unknown'::{TEMPERATURE_TYPE_ENUM_NAME}"),
        ),
        sa.Column(
            "calibration_status",
            _enum(CALIBRATION_STATUS_ENUM_NAME, CALIBRATION_STATUSES),
            nullable=False,
            server_default=sa.text(f"'unknown'::{CALIBRATION_STATUS_ENUM_NAME}"),
        ),
        sa.Column("calibrated_at", sa.DateTime, nullable=True),
        sa.Column("calibration_reference", sa.String(255), nullable=True),
        sa.Column("effective_from", sa.DateTime, nullable=True),
        sa.Column("effective_to", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_weather_device_mappings_site", "weather_device_mappings", ["site_id"]
    )
    op.create_index(
        "ix_weather_device_mappings_device", "weather_device_mappings", ["device_id"]
    )
    op.create_index(
        "ix_weather_device_mappings_source",
        "weather_device_mappings",
        ["weather_source_id"],
    )

    # ------------------------------------------------------------------
    # 7. expected_weather_provenance  (placeholder; not written in W0)
    # ------------------------------------------------------------------
    op.create_table(
        "expected_weather_provenance",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "weather_source_id",
            sa.Integer,
            sa.ForeignKey("weather_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "profile_id",
            sa.Integer,
            sa.ForeignKey("weather_source_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("computed_at", sa.DateTime, nullable=True),
        sa.Column("window_start", sa.DateTime, nullable=True),
        sa.Column("window_end", sa.DateTime, nullable=True),
        sa.Column("bucket_size", sa.String(16), nullable=True),
        sa.Column(
            "is_modeled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "confidence",
            _enum(CONFIDENCE_ENUM_NAME, CONFIDENCES),
            nullable=False,
            server_default=sa.text(f"'unknown'::{CONFIDENCE_ENUM_NAME}"),
        ),
        sa.Column("coverage_pct", sa.Numeric, nullable=True),
        sa.Column("missing_input_buckets", sa.Integer, nullable=True),
        sa.Column("summary_json", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_expected_weather_provenance_site",
        "expected_weather_provenance",
        ["site_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        "ix_expected_weather_provenance_site",
        table_name="expected_weather_provenance",
    )
    op.drop_table("expected_weather_provenance")

    op.drop_index(
        "ix_weather_device_mappings_source", table_name="weather_device_mappings"
    )
    op.drop_index(
        "ix_weather_device_mappings_device", table_name="weather_device_mappings"
    )
    op.drop_index(
        "ix_weather_device_mappings_site", table_name="weather_device_mappings"
    )
    op.drop_table("weather_device_mappings")

    op.drop_index(
        "ix_weather_source_approvals_target", table_name="weather_source_approvals"
    )
    op.drop_index(
        "ix_weather_source_approvals_site", table_name="weather_source_approvals"
    )
    op.drop_table("weather_source_approvals")

    op.drop_index(
        "ix_weather_observations_site_metric_ts", table_name="weather_observations"
    )
    op.drop_index("ix_weather_observations_source", table_name="weather_observations")
    op.drop_index("ix_weather_observations_batch", table_name="weather_observations")
    op.drop_index("ix_weather_observations_site", table_name="weather_observations")
    op.drop_table("weather_observations")

    op.drop_index(
        "ix_weather_observation_batches_source",
        table_name="weather_observation_batches",
    )
    op.drop_index(
        "ix_weather_observation_batches_site",
        table_name="weather_observation_batches",
    )
    op.drop_table("weather_observation_batches")

    op.drop_index(
        "ix_weather_source_profiles_status", table_name="weather_source_profiles"
    )
    op.drop_index(
        "ix_weather_source_profiles_role", table_name="weather_source_profiles"
    )
    op.drop_index(
        "ix_weather_source_profiles_source", table_name="weather_source_profiles"
    )
    op.drop_index(
        "ix_weather_source_profiles_site", table_name="weather_source_profiles"
    )
    op.drop_table("weather_source_profiles")

    op.drop_index("ix_weather_sources_type", table_name="weather_sources")
    op.drop_index("ix_weather_sources_site", table_name="weather_sources")
    op.drop_index("ix_weather_sources_company", table_name="weather_sources")
    op.drop_table("weather_sources")

    for name in (
        APPROVAL_ACTION_ENUM_NAME,
        APPROVAL_TARGET_TYPE_ENUM_NAME,
        CALIBRATION_STATUS_ENUM_NAME,
        CONFIDENCE_ENUM_NAME,
        TEMPERATURE_TYPE_ENUM_NAME,
        IRRADIANCE_PLANE_ENUM_NAME,
        BATCH_KIND_ENUM_NAME,
        PROFILE_STATUS_ENUM_NAME,
        PROFILE_ROLE_ENUM_NAME,
        SOURCE_TYPE_ENUM_NAME,
    ):
        postgresql.ENUM(name=name, create_type=False).drop(bind, checkfirst=True)
