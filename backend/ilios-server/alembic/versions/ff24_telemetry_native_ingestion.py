"""Native V2 telemetry ingestion: metric catalog, sync jobs, readings, rollups.

Revision ID: ff24_telemetry_native_ingestion
Revises: ff23_telemetry_external_devices
Create Date: 2026-06-10

Background
----------
Replaces the legacy GCP/BigQuery telemetry *pull* with a native, in-app
ingestion path. This migration adds the durable schema that the ingestion
service writes to:

* ``telemetry_metric_catalog`` — provider field -> normalized metric mapping,
  seeded from the legacy AlsoEnergy point-tag map.
* ``telemetry_sync_jobs`` — one row per ingestion attempt (success, partial, or
  failure), modelled on ``finance_sync_runs``.
* ``telemetry_readings`` — the normalized readings store, carrying the full
  provenance hierarchy (company -> provider account -> external site -> iliOS
  site -> external device -> iliOS device -> normalized metric). Idempotent via
  ``uq_telemetry_readings_dedupe``.
* ``telemetry_site_interval_rollups`` / ``telemetry_device_interval_rollups`` —
  derived per-bucket aggregates; idempotent per window.

Three new Postgres enum types are created
(``telemetry_sync_status_enum``, ``telemetry_sync_scope_enum``,
``telemetry_sync_trigger_enum``). Each is used by exactly one column on
``telemetry_sync_jobs``.

Design note (deviation from the bare spec column list)
------------------------------------------------------
``telemetry_metric_catalog`` carries TWO provider field names:
``provider_field_name`` (the name in a device's ``fieldsArchived`` list, used
for discovery + response verification) and ``provider_query_field`` (the
canonical field sent as the BinData request ``fieldName``). AlsoEnergy uses
different identifiers for discovery vs. query (e.g. ``KwAC`` -> ``Active_Power``),
so both are required to faithfully replicate the legacy contract without
inventing any provider behaviour.

The ``Sun`` (POA) and ``Sun2`` (GHI) rows intentionally share the
``irradiance_wm2`` normalized metric; the ingestion service treats a device
exposing both as ambiguous and skips it, mirroring the legacy pipeline.

This migration is ADDITIVE ONLY. It does not touch the ``sites`` table or any
existing telemetry table/enum.

Rollback
--------
``downgrade()`` drops the five tables (children first) and the three new enum
types.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff24_telemetry_native_ingestion"
down_revision = "ff23_telemetry_external_devices"
branch_labels = None
depends_on = None


SYNC_STATUS_ENUM_NAME = "telemetry_sync_status_enum"
SYNC_SCOPE_ENUM_NAME = "telemetry_sync_scope_enum"
SYNC_TRIGGER_ENUM_NAME = "telemetry_sync_trigger_enum"

SYNC_STATUSES = ("queued", "running", "succeeded", "partial", "failed")
SYNC_SCOPES = ("site", "company", "portfolio")
SYNC_TRIGGERS = ("manual", "scheduled", "backfill")

# Seeded from backend/rea-telemetry .../common/constants.py POINT_TAG_MAP for
# DataProvider.ALSO_ENERGY. Tuple shape:
#   (provider_field_name, provider_query_field, normalized_metric, unit, device_category)
# Units come from the legacy PointTag enum comments.
ALSO_ENERGY_METRIC_SEED = (
    ("KwAC", "Active_Power", "device_power_ac_kw", "kW", "inverter"),
    ("KW", "Active_Power", "site_power_ac_kw", "kW", None),
    ("Temp1", "Temp_Module", "cell_temperature_f", "\u00b0F", None),
    ("Sun", "POA_Irradiance", "irradiance_wm2", "W/m\u00b2", None),
    ("Sun2", "GHI_Irradiance", "irradiance_wm2", "W/m\u00b2", None),
)


def upgrade() -> None:
    bind = op.get_bind()

    sync_status_enum = postgresql.ENUM(
        *SYNC_STATUSES, name=SYNC_STATUS_ENUM_NAME, create_type=False
    )
    sync_scope_enum = postgresql.ENUM(
        *SYNC_SCOPES, name=SYNC_SCOPE_ENUM_NAME, create_type=False
    )
    sync_trigger_enum = postgresql.ENUM(
        *SYNC_TRIGGERS, name=SYNC_TRIGGER_ENUM_NAME, create_type=False
    )
    sync_status_enum.create(bind, checkfirst=True)
    sync_scope_enum.create(bind, checkfirst=True)
    sync_trigger_enum.create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # telemetry_metric_catalog
    # ------------------------------------------------------------------
    metric_catalog = op.create_table(
        "telemetry_metric_catalog",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("provider_field_name", sa.String(255), nullable=False),
        sa.Column("provider_query_field", sa.String(255), nullable=True),
        sa.Column("normalized_metric", sa.String(64), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("device_category", sa.String(64), nullable=True),
        sa.Column(
            "is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "provider_key",
            "provider_field_name",
            name="uq_telemetry_metric_catalog_provider_field",
        ),
    )
    op.create_index(
        "ix_telemetry_metric_catalog_provider",
        "telemetry_metric_catalog",
        ["provider_key"],
    )

    # ------------------------------------------------------------------
    # telemetry_sync_jobs
    # ------------------------------------------------------------------
    op.create_table(
        "telemetry_sync_jobs",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider_account_id",
            sa.Integer,
            sa.ForeignKey("das_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "scope",
            postgresql.ENUM(*SYNC_SCOPES, name=SYNC_SCOPE_ENUM_NAME, create_type=False),
            nullable=False,
            server_default=sa.text(f"'site'::{SYNC_SCOPE_ENUM_NAME}"),
        ),
        sa.Column(
            "status",
            postgresql.ENUM(*SYNC_STATUSES, name=SYNC_STATUS_ENUM_NAME, create_type=False),
            nullable=False,
            server_default=sa.text(f"'queued'::{SYNC_STATUS_ENUM_NAME}"),
        ),
        sa.Column(
            "trigger",
            postgresql.ENUM(
                *SYNC_TRIGGERS, name=SYNC_TRIGGER_ENUM_NAME, create_type=False
            ),
            nullable=False,
            server_default=sa.text(f"'manual'::{SYNC_TRIGGER_ENUM_NAME}"),
        ),
        sa.Column("window_start", sa.DateTime, nullable=True),
        sa.Column("window_end", sa.DateTime, nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=False),
        sa.Column(
            "triggered_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "records_requested", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "records_received", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "records_written", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("stats_json", postgresql.JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("ended_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_telemetry_sync_jobs_company", "telemetry_sync_jobs", ["company_id"]
    )
    op.create_index("ix_telemetry_sync_jobs_site", "telemetry_sync_jobs", ["site_id"])
    op.create_index("ix_telemetry_sync_jobs_status", "telemetry_sync_jobs", ["status"])
    op.create_index(
        "ix_telemetry_sync_jobs_started_at", "telemetry_sync_jobs", ["started_at"]
    )

    # ------------------------------------------------------------------
    # telemetry_readings
    # ------------------------------------------------------------------
    op.create_table(
        "telemetry_readings",
        sa.Column(
            "id", sa.BigInteger, sa.Identity(start=1, increment=1), primary_key=True
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider_account_id",
            sa.Integer,
            sa.ForeignKey("das_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_site_id", sa.String(255), nullable=False),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_device_id", sa.String(255), nullable=True),
        sa.Column(
            "device_id",
            sa.Integer,
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dedupe_key", sa.String(255), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("provider_metric", sa.String(255), nullable=False),
        sa.Column("normalized_metric", sa.String(64), nullable=False),
        sa.Column("metric_ts", sa.DateTime, nullable=False),
        sa.Column("value", sa.Numeric, nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("quality", sa.String(32), nullable=True),
        sa.Column(
            "sync_job_id",
            sa.Integer,
            sa.ForeignKey("telemetry_sync_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "provider_account_id",
            "dedupe_key",
            "provider_metric",
            "metric_ts",
            name="uq_telemetry_readings_dedupe",
        ),
    )
    op.create_index(
        "ix_telemetry_readings_site_ts",
        "telemetry_readings",
        ["site_id", "metric_ts"],
    )
    op.create_index(
        "ix_telemetry_readings_device_ts",
        "telemetry_readings",
        ["device_id", "metric_ts"],
    )
    op.create_index(
        "ix_telemetry_readings_sync_job", "telemetry_readings", ["sync_job_id"]
    )

    # ------------------------------------------------------------------
    # telemetry_site_interval_rollups
    # ------------------------------------------------------------------
    op.create_table(
        "telemetry_site_interval_rollups",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bucket_start", sa.DateTime, nullable=False),
        sa.Column("bucket_size", sa.String(16), nullable=False),
        sa.Column("normalized_metric", sa.String(64), nullable=False),
        sa.Column("agg", sa.String(16), nullable=False),
        sa.Column("value", sa.Numeric, nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column(
            "sample_count", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column("completeness", sa.Numeric, nullable=True),
        sa.Column(
            "calculated_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "site_id",
            "bucket_start",
            "bucket_size",
            "normalized_metric",
            name="uq_telemetry_site_rollup",
        ),
    )
    op.create_index(
        "ix_telemetry_site_rollup_site_bucket",
        "telemetry_site_interval_rollups",
        ["site_id", "bucket_start"],
    )

    # ------------------------------------------------------------------
    # telemetry_device_interval_rollups
    # ------------------------------------------------------------------
    op.create_table(
        "telemetry_device_interval_rollups",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "device_id",
            sa.Integer,
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bucket_start", sa.DateTime, nullable=False),
        sa.Column("bucket_size", sa.String(16), nullable=False),
        sa.Column("normalized_metric", sa.String(64), nullable=False),
        sa.Column("agg", sa.String(16), nullable=False),
        sa.Column("value", sa.Numeric, nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column(
            "sample_count", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column("completeness", sa.Numeric, nullable=True),
        sa.Column(
            "calculated_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "device_id",
            "bucket_start",
            "bucket_size",
            "normalized_metric",
            name="uq_telemetry_device_rollup",
        ),
    )
    op.create_index(
        "ix_telemetry_device_rollup_device_bucket",
        "telemetry_device_interval_rollups",
        ["device_id", "bucket_start"],
    )
    op.create_index(
        "ix_telemetry_device_rollup_site",
        "telemetry_device_interval_rollups",
        ["site_id"],
    )

    # ------------------------------------------------------------------
    # Seed: AlsoEnergy metric catalog
    # ------------------------------------------------------------------
    op.bulk_insert(
        metric_catalog,
        [
            {
                "provider_key": "also_energy",
                "provider_field_name": field_name,
                "provider_query_field": query_field,
                "normalized_metric": normalized_metric,
                "unit": unit,
                "device_category": device_category,
                "is_enabled": True,
            }
            for (
                field_name,
                query_field,
                normalized_metric,
                unit,
                device_category,
            ) in ALSO_ENERGY_METRIC_SEED
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        "ix_telemetry_device_rollup_site",
        table_name="telemetry_device_interval_rollups",
    )
    op.drop_index(
        "ix_telemetry_device_rollup_device_bucket",
        table_name="telemetry_device_interval_rollups",
    )
    op.drop_table("telemetry_device_interval_rollups")

    op.drop_index(
        "ix_telemetry_site_rollup_site_bucket",
        table_name="telemetry_site_interval_rollups",
    )
    op.drop_table("telemetry_site_interval_rollups")

    op.drop_index("ix_telemetry_readings_sync_job", table_name="telemetry_readings")
    op.drop_index("ix_telemetry_readings_device_ts", table_name="telemetry_readings")
    op.drop_index("ix_telemetry_readings_site_ts", table_name="telemetry_readings")
    op.drop_table("telemetry_readings")

    op.drop_index("ix_telemetry_sync_jobs_started_at", table_name="telemetry_sync_jobs")
    op.drop_index("ix_telemetry_sync_jobs_status", table_name="telemetry_sync_jobs")
    op.drop_index("ix_telemetry_sync_jobs_site", table_name="telemetry_sync_jobs")
    op.drop_index("ix_telemetry_sync_jobs_company", table_name="telemetry_sync_jobs")
    op.drop_table("telemetry_sync_jobs")

    op.drop_index(
        "ix_telemetry_metric_catalog_provider",
        table_name="telemetry_metric_catalog",
    )
    op.drop_table("telemetry_metric_catalog")

    postgresql.ENUM(name=SYNC_TRIGGER_ENUM_NAME, create_type=False).drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(name=SYNC_SCOPE_ENUM_NAME, create_type=False).drop(
        bind, checkfirst=True
    )
    postgresql.ENUM(name=SYNC_STATUS_ENUM_NAME, create_type=False).drop(
        bind, checkfirst=True
    )
