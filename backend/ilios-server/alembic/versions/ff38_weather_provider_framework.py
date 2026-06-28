"""Third-Party Weather Provider Framework (Phases A–D) — additive provider plumbing.

Revision ID: ff38_weather_provider_framework
Revises: ff36_task_inventory_mismatch_provenance
Create Date: 2026-06-28

Background
----------
Adds the DB plumbing for a third-party weather provider framework that pulls
EXTERNAL, CONTEXT-ONLY weather (e.g. Open-Meteo) into the existing W0 weather
domain. It is strictly additive and changes NO existing behavior:

* ``weather_provider_catalog`` — DB-backed registry of provider adapters
  (mirrors ``telemetry_provider_catalog``). Seeded ``is_enabled=false`` so every
  provider stays dark until explicitly turned on. ``capabilities_json`` is a
  descriptive snapshot only; the framework never marks an external provider as
  expected-/physics-eligible.
* ``weather_provider_accounts`` — per-company credential REFERENCE rows for
  keyed providers (mirrors the telemetry ``das_connections`` v2 account). Only a
  ``secret_name`` reference is stored; the API key itself lives in the durable
  credential store, never in the DB. Keyless providers need no account.
* Six additive NULLable columns on ``weather_observation_batches`` recording how
  a provider pull went (account, status, request/response hashes, api version,
  error summary). They are populated only on ``provider_pull`` batches and never
  change what observations MEAN.

Hard invariants (mirrors ``app/models/weather.py``): external GHI/ambient stays
context-only — no GHI→POA, no ambient→cell, no resolver/expected/baseline change,
no scheduler, no paid-provider commitment, no API keys committed. Additive only.

Rollback
--------
``downgrade()`` drops the six batch columns, then the two new tables, then the
four new enum types. The seeded Open-Meteo catalog row is removed with the
catalog table. No pre-existing object is touched.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff38_weather_provider_framework"
down_revision = "ff36_task_inventory_mismatch_provenance"
branch_labels = None
depends_on = None


# Enum type names (kept in lockstep with app/models/weather.py).
PROVIDER_PULL_STATUS_ENUM_NAME = "weather_provider_pull_status_enum"
PROVIDER_ACCOUNT_STATUS_ENUM_NAME = "weather_provider_account_status_enum"
PROVIDER_CREDENTIAL_STATUS_ENUM_NAME = "weather_provider_credential_status_enum"
PROVIDER_SYNC_STATUS_ENUM_NAME = "weather_provider_sync_status_enum"

PROVIDER_PULL_STATUSES = ("succeeded", "partial", "failed")
PROVIDER_ACCOUNT_STATUSES = ("active", "paused", "archived")
PROVIDER_CREDENTIAL_STATUSES = ("unverified", "verified", "invalid", "expired")
PROVIDER_SYNC_STATUSES = ("never", "success", "partial", "failed")

# Open-Meteo seed (keyless, free for non-commercial use). Seeded DISABLED.
_OPEN_METEO_CAPABILITIES_JSON = (
    '{'
    '"supports_historical": true, '
    '"supports_forecast": false, '
    '"metrics": ["air_temperature", "ghi_irradiance"], '
    '"native_plane": "ghi", '
    '"native_temperature_type": "ambient", '
    '"is_modeled": true, '
    '"min_granularity_minutes": 60, '
    '"max_history_days": null, '
    '"rate_limit": {"requests_per_minute": 60, "requests_per_day": 5000, '
    '"max_concurrent": 1}, '
    '"licensing_class": "free_noncommercial", '
    '"expected_eligible_capable": false'
    '}'
)


def _enum(name, values):
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # Enum types (created once; columns reference them with create_type=False)
    # ------------------------------------------------------------------
    enum_defs = (
        (PROVIDER_PULL_STATUS_ENUM_NAME, PROVIDER_PULL_STATUSES),
        (PROVIDER_ACCOUNT_STATUS_ENUM_NAME, PROVIDER_ACCOUNT_STATUSES),
        (PROVIDER_CREDENTIAL_STATUS_ENUM_NAME, PROVIDER_CREDENTIAL_STATUSES),
        (PROVIDER_SYNC_STATUS_ENUM_NAME, PROVIDER_SYNC_STATUSES),
    )
    for name, values in enum_defs:
        _enum(name, values).create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # 1. weather_provider_catalog
    # ------------------------------------------------------------------
    op.create_table(
        "weather_provider_catalog",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("adapter_class", sa.String(255), nullable=False),
        sa.Column(
            "config_schema",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("capabilities_json", postgresql.JSONB, nullable=True),
        sa.Column("licensing_class", sa.String(64), nullable=True),
        sa.Column("docs_url", sa.String(512), nullable=True),
        sa.Column(
            "is_enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ------------------------------------------------------------------
    # 2. weather_provider_accounts
    # ------------------------------------------------------------------
    op.create_table(
        "weather_provider_accounts",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("secret_name", sa.String(255), nullable=True),
        sa.Column("external_account_label", sa.String(255), nullable=True),
        sa.Column(
            "status",
            _enum(PROVIDER_ACCOUNT_STATUS_ENUM_NAME, PROVIDER_ACCOUNT_STATUSES),
            nullable=False,
            server_default=sa.text(f"'active'::{PROVIDER_ACCOUNT_STATUS_ENUM_NAME}"),
        ),
        sa.Column(
            "credential_status",
            _enum(
                PROVIDER_CREDENTIAL_STATUS_ENUM_NAME, PROVIDER_CREDENTIAL_STATUSES
            ),
            nullable=False,
            server_default=sa.text(
                f"'unverified'::{PROVIDER_CREDENTIAL_STATUS_ENUM_NAME}"
            ),
        ),
        sa.Column(
            "last_sync_status",
            _enum(PROVIDER_SYNC_STATUS_ENUM_NAME, PROVIDER_SYNC_STATUSES),
            nullable=False,
            server_default=sa.text(f"'never'::{PROVIDER_SYNC_STATUS_ENUM_NAME}"),
        ),
        sa.Column(
            "licensing_acknowledged_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("licensing_acknowledged_at", sa.DateTime, nullable=True),
        sa.Column("last_success_at", sa.DateTime, nullable=True),
        sa.Column("last_error_at", sa.DateTime, nullable=True),
        sa.Column("last_error_message", sa.String(1000), nullable=True),
        sa.Column(
            "is_archived",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("archived_at", sa.DateTime, nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_weather_provider_accounts_company",
        "weather_provider_accounts",
        ["company_id"],
    )
    op.create_index(
        "ix_weather_provider_accounts_provider",
        "weather_provider_accounts",
        ["provider_key"],
    )

    # ------------------------------------------------------------------
    # 3. Additive provider-pull provenance columns on weather_observation_batches
    #    (all NULLable; populated only on batch_kind='provider_pull').
    # ------------------------------------------------------------------
    op.add_column(
        "weather_observation_batches",
        sa.Column(
            "account_id",
            sa.Integer,
            sa.ForeignKey("weather_provider_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "weather_observation_batches",
        sa.Column(
            "pull_status",
            _enum(PROVIDER_PULL_STATUS_ENUM_NAME, PROVIDER_PULL_STATUSES),
            nullable=True,
        ),
    )
    op.add_column(
        "weather_observation_batches",
        sa.Column("provider_request_hash", sa.String(128), nullable=True),
    )
    op.add_column(
        "weather_observation_batches",
        sa.Column("provider_response_hash", sa.String(128), nullable=True),
    )
    op.add_column(
        "weather_observation_batches",
        sa.Column("provider_api_version", sa.String(64), nullable=True),
    )
    op.add_column(
        "weather_observation_batches",
        sa.Column("error_summary", sa.Text, nullable=True),
    )

    # ------------------------------------------------------------------
    # 4. Seed the Open-Meteo provider (keyless, DISABLED). Idempotent.
    # ------------------------------------------------------------------
    op.execute(
        f"""
        INSERT INTO weather_provider_catalog
            (provider_key, display_name, adapter_class, config_schema,
             capabilities_json, licensing_class, docs_url, is_enabled,
             created_at, updated_at)
        VALUES
            ('open_meteo', 'Open-Meteo',
             'app.integrations.weather.openmeteo_adapter.OpenMeteoAdapter',
             '{{}}'::jsonb,
             '{_OPEN_METEO_CAPABILITIES_JSON}'::jsonb,
             'free_noncommercial',
             'https://open-meteo.com/en/docs/historical-weather-api',
             FALSE, NOW(), NOW())
        ON CONFLICT (provider_key) DO NOTHING
        """
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_column("weather_observation_batches", "error_summary")
    op.drop_column("weather_observation_batches", "provider_api_version")
    op.drop_column("weather_observation_batches", "provider_response_hash")
    op.drop_column("weather_observation_batches", "provider_request_hash")
    op.drop_column("weather_observation_batches", "pull_status")
    op.drop_column("weather_observation_batches", "account_id")

    op.drop_index(
        "ix_weather_provider_accounts_provider",
        table_name="weather_provider_accounts",
    )
    op.drop_index(
        "ix_weather_provider_accounts_company",
        table_name="weather_provider_accounts",
    )
    op.drop_table("weather_provider_accounts")

    op.drop_table("weather_provider_catalog")

    for name in (
        PROVIDER_SYNC_STATUS_ENUM_NAME,
        PROVIDER_CREDENTIAL_STATUS_ENUM_NAME,
        PROVIDER_ACCOUNT_STATUS_ENUM_NAME,
        PROVIDER_PULL_STATUS_ENUM_NAME,
    ):
        postgresql.ENUM(name=name, create_type=False).drop(bind, checkfirst=True)
