"""Telemetry refactor Phase 1 — additive v2 schema introduction.

Revision ID: ff18_telemetry_v2_introduce
Revises: ff17_add_poison_pill_to_document_keys
Create Date: 2026-04-25

Phase 1 of the telemetry refactor. This migration is intentionally
ADDITIVE ONLY — no columns or tables are dropped, no types are changed,
no NOT NULL constraints are tightened on existing columns. The legacy
flow continues to function unchanged. New code paths under
/api/telemetry/v2/ use the columns and tables introduced here.

Adds:
  - Table  `telemetry_provider_catalog`               (DB-backed catalog)
  - Table  `telemetry_external_sites`                 (synced provenance)
  - ENUM   `provider_account_status_enum`             (lifecycle states)
  - ENUM   `credential_status_enum`                   (credential health)
  - ENUM   `last_sync_status_enum`                    (last attempt result)
  - ENUM   `external_site_sync_status_enum`           (per-row provenance)
  - ENUM   `company_provider_status_enum`             (license status)
  - Cols on company_das_providers: catalog_id, status, notes, updated_at
  - Cols on das_connections: company_provider_id, status, credential_status,
      last_sync_status, external_account_label, last_success_at,
      last_error_at, last_error_message, is_archived, archived_at,
      created_by_user_id
  - Cols on telemetry_sites_mapping: provider_account_id, mapping_role,
      is_active
  - Cols on telemetry_devices_mapping: provider_account_id, device_role,
      is_active
  - Seeds two catalog rows (`also_energy`, `kmc`) and backfills
    catalog_id / company_provider_id for existing data.
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff18_telemetry_v2_introduce"
down_revision = "ff17_add_poison_pill_to_document_keys"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROVIDER_ACCOUNT_STATUSES = ("active", "paused", "archived")
CREDENTIAL_STATUSES = ("unverified", "verified", "invalid", "expired")
LAST_SYNC_STATUSES = ("never", "success", "partial", "failed")
EXTERNAL_SITE_SYNC_STATUSES = ("seen", "missing", "stale")
COMPANY_PROVIDER_STATUSES = ("active", "suspended")


def _make_enum(name: str, values: tuple[str, ...]) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    bind = op.get_bind()

    # ----- Enums --------------------------------------------------------
    sa.Enum(*PROVIDER_ACCOUNT_STATUSES, name="provider_account_status_enum").create(bind, checkfirst=True)
    sa.Enum(*CREDENTIAL_STATUSES, name="credential_status_enum").create(bind, checkfirst=True)
    sa.Enum(*LAST_SYNC_STATUSES, name="last_sync_status_enum").create(bind, checkfirst=True)
    sa.Enum(*EXTERNAL_SITE_SYNC_STATUSES, name="external_site_sync_status_enum").create(bind, checkfirst=True)
    sa.Enum(*COMPANY_PROVIDER_STATUSES, name="company_provider_status_enum").create(bind, checkfirst=True)

    # ----- telemetry_provider_catalog -----------------------------------
    op.create_table(
        "telemetry_provider_catalog",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("provider_key", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("adapter_class", sa.String(255), nullable=False),
        sa.Column("config_schema", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("docs_url", sa.String(512), nullable=True),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_telemetry_provider_catalog_enabled",
        "telemetry_provider_catalog",
        ["is_enabled"],
    )

    # ----- telemetry_external_sites -------------------------------------
    op.create_table(
        "telemetry_external_sites",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "provider_account_id",
            sa.Integer,
            sa.ForeignKey("das_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_site_id", sa.String(255), nullable=False),
        sa.Column("external_site_name", sa.String(512), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB, nullable=True),
        sa.Column("first_seen_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_synced_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_sync_run_id", sa.String(64), nullable=True),
        sa.Column(
            "sync_status",
            _make_enum("external_site_sync_status_enum", EXTERNAL_SITE_SYNC_STATUSES),
            nullable=False,
            server_default=sa.text("'seen'::external_site_sync_status_enum"),
        ),
        sa.Column("last_sync_error", sa.String(1000), nullable=True),
        sa.UniqueConstraint(
            "provider_account_id",
            "external_site_id",
            name="uq_telemetry_external_sites_account_extid",
        ),
    )
    op.create_index(
        "ix_telemetry_external_sites_account",
        "telemetry_external_sites",
        ["provider_account_id"],
    )
    op.create_index(
        "ix_telemetry_external_sites_status",
        "telemetry_external_sites",
        ["provider_account_id", "sync_status"],
    )

    # ----- company_das_providers (license rows) -------------------------
    op.add_column(
        "company_das_providers",
        sa.Column(
            "catalog_id",
            sa.Integer,
            sa.ForeignKey("telemetry_provider_catalog.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "company_das_providers",
        sa.Column(
            "status",
            _make_enum("company_provider_status_enum", COMPANY_PROVIDER_STATUSES),
            nullable=False,
            server_default=sa.text("'active'::company_provider_status_enum"),
        ),
    )
    op.add_column(
        "company_das_providers",
        sa.Column("notes", sa.String(1000), nullable=True),
    )
    op.add_column(
        "company_das_providers",
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_company_das_providers_catalog",
        "company_das_providers",
        ["catalog_id"],
    )

    # ----- das_connections (provider accounts) --------------------------
    op.add_column(
        "das_connections",
        sa.Column(
            "company_provider_id",
            sa.Integer,
            sa.ForeignKey("company_das_providers.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )
    op.add_column(
        "das_connections",
        sa.Column(
            "status",
            _make_enum("provider_account_status_enum", PROVIDER_ACCOUNT_STATUSES),
            nullable=False,
            server_default=sa.text("'active'::provider_account_status_enum"),
        ),
    )
    op.add_column(
        "das_connections",
        sa.Column(
            "credential_status",
            _make_enum("credential_status_enum", CREDENTIAL_STATUSES),
            nullable=False,
            server_default=sa.text("'unverified'::credential_status_enum"),
        ),
    )
    op.add_column(
        "das_connections",
        sa.Column(
            "last_sync_status",
            _make_enum("last_sync_status_enum", LAST_SYNC_STATUSES),
            nullable=False,
            server_default=sa.text("'never'::last_sync_status_enum"),
        ),
    )
    op.add_column(
        "das_connections",
        sa.Column("external_account_label", sa.String(255), nullable=True),
    )
    op.add_column(
        "das_connections",
        sa.Column("last_success_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "das_connections",
        sa.Column("last_error_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "das_connections",
        sa.Column("last_error_message", sa.String(1000), nullable=True),
    )
    op.add_column(
        "das_connections",
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "das_connections",
        sa.Column("archived_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "das_connections",
        sa.Column(
            "created_by_user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_das_connections_company_provider",
        "das_connections",
        ["company_provider_id"],
    )
    op.create_index(
        "ix_das_connections_status",
        "das_connections",
        ["company_id", "status", "is_archived"],
    )

    # ----- telemetry_sites_mapping --------------------------------------
    op.add_column(
        "telemetry_sites_mapping",
        sa.Column(
            "provider_account_id",
            sa.Integer,
            sa.ForeignKey("das_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "telemetry_sites_mapping",
        sa.Column("mapping_role", sa.String(32), nullable=False, server_default=sa.text("'primary'")),
    )
    op.add_column(
        "telemetry_sites_mapping",
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )
    op.create_index(
        "ix_telemetry_sites_mapping_provider_account",
        "telemetry_sites_mapping",
        ["provider_account_id"],
    )

    # ----- telemetry_devices_mapping ------------------------------------
    op.add_column(
        "telemetry_devices_mapping",
        sa.Column(
            "provider_account_id",
            sa.Integer,
            sa.ForeignKey("das_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "telemetry_devices_mapping",
        sa.Column("device_role", sa.String(32), nullable=False, server_default=sa.text("'primary'")),
    )
    op.add_column(
        "telemetry_devices_mapping",
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
    )
    op.create_index(
        "ix_telemetry_devices_mapping_provider_account",
        "telemetry_devices_mapping",
        ["provider_account_id"],
    )

    # ----- Seed catalog rows (idempotent) -------------------------------
    # Use ON CONFLICT so re-running this migration on a partially seeded
    # database (or re-stamping from an older revision) is safe.
    op.execute(
        """
        INSERT INTO telemetry_provider_catalog
            (provider_key, display_name, adapter_class, config_schema,
             docs_url, is_enabled, created_at, updated_at)
        VALUES
            ('also_energy', 'Also Energy',
             'app.integrations.telemetry.also_energy_adapter.AlsoEnergyAdapter',
             '{"type":"object","required":["username","password"],"properties":{"username":{"type":"string","title":"Username"},"password":{"type":"string","title":"Password","format":"password"}}}'::jsonb,
             NULL, TRUE, NOW(), NOW()),
            ('kmc', 'KMC',
             'app.integrations.telemetry.kmc_adapter.KmcAdapter',
             '{"type":"object","required":["token"],"properties":{"token":{"type":"string","title":"API Token","format":"password"}}}'::jsonb,
             NULL, TRUE, NOW(), NOW())
        ON CONFLICT (provider_key) DO NOTHING
        """
    )

    # ----- Backfill catalog_id on existing licenses ---------------------
    op.execute(
        """
        UPDATE company_das_providers cdp
        SET catalog_id = tpc.id
        FROM telemetry_provider_catalog tpc
        WHERE cdp.catalog_id IS NULL
          AND tpc.provider_key = cdp.provider::text
        """
    )

    # ----- Backfill company_provider_id on existing accounts ------------
    op.execute(
        """
        UPDATE das_connections dc
        SET company_provider_id = cdp.id
        FROM company_das_providers cdp
        WHERE dc.company_provider_id IS NULL
          AND cdp.company_id = dc.company_id
          AND cdp.provider = dc.provider
        """
    )

    # ----- Backfill provider_account_id on existing mappings ------------
    op.execute(
        """
        UPDATE telemetry_sites_mapping tsm
        SET provider_account_id = tsm.connection_id
        WHERE tsm.provider_account_id IS NULL
          AND tsm.connection_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE telemetry_devices_mapping tdm
        SET provider_account_id = tsm.connection_id
        FROM telemetry_sites_mapping tsm, devices d
        WHERE tdm.provider_account_id IS NULL
          AND tdm.device_id = d.id
          AND tsm.site_id = d.site_id
        """
    )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    # telemetry_devices_mapping
    op.drop_index("ix_telemetry_devices_mapping_provider_account", table_name="telemetry_devices_mapping")
    op.drop_column("telemetry_devices_mapping", "is_active")
    op.drop_column("telemetry_devices_mapping", "device_role")
    op.drop_column("telemetry_devices_mapping", "provider_account_id")

    # telemetry_sites_mapping
    op.drop_index("ix_telemetry_sites_mapping_provider_account", table_name="telemetry_sites_mapping")
    op.drop_column("telemetry_sites_mapping", "is_active")
    op.drop_column("telemetry_sites_mapping", "mapping_role")
    op.drop_column("telemetry_sites_mapping", "provider_account_id")

    # das_connections
    op.drop_index("ix_das_connections_status", table_name="das_connections")
    op.drop_index("ix_das_connections_company_provider", table_name="das_connections")
    op.drop_column("das_connections", "created_by_user_id")
    op.drop_column("das_connections", "archived_at")
    op.drop_column("das_connections", "is_archived")
    op.drop_column("das_connections", "last_error_message")
    op.drop_column("das_connections", "last_error_at")
    op.drop_column("das_connections", "last_success_at")
    op.drop_column("das_connections", "external_account_label")
    op.drop_column("das_connections", "last_sync_status")
    op.drop_column("das_connections", "credential_status")
    op.drop_column("das_connections", "status")
    op.drop_column("das_connections", "company_provider_id")

    # company_das_providers
    op.drop_index("ix_company_das_providers_catalog", table_name="company_das_providers")
    op.drop_column("company_das_providers", "updated_at")
    op.drop_column("company_das_providers", "notes")
    op.drop_column("company_das_providers", "status")
    op.drop_column("company_das_providers", "catalog_id")

    # New tables
    op.drop_index("ix_telemetry_external_sites_status", table_name="telemetry_external_sites")
    op.drop_index("ix_telemetry_external_sites_account", table_name="telemetry_external_sites")
    op.drop_table("telemetry_external_sites")

    op.drop_index("ix_telemetry_provider_catalog_enabled", table_name="telemetry_provider_catalog")
    op.drop_table("telemetry_provider_catalog")

    bind = op.get_bind()
    sa.Enum(name="company_provider_status_enum").drop(bind, checkfirst=True)
    sa.Enum(name="external_site_sync_status_enum").drop(bind, checkfirst=True)
    sa.Enum(name="last_sync_status_enum").drop(bind, checkfirst=True)
    sa.Enum(name="credential_status_enum").drop(bind, checkfirst=True)
    sa.Enum(name="provider_account_status_enum").drop(bind, checkfirst=True)
