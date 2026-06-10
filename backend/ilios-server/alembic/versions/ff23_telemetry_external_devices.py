"""Add telemetry_external_devices cache table (V2 device mapping).

Revision ID: ff23_telemetry_external_devices
Revises: ff22_site_mapping_provenance
Create Date: 2026-06-10

Background
----------
The V2 (DB-backed) Telemetry Setup Wizard "Device Mapping" step must read the
list of provider devices from iliOS rather than making a live Cloud Function /
Firestore call. This migration adds a per-site device cache that mirrors
``telemetry_external_sites`` one level down.

A device row is uniquely identified by
``{provider_account_id, external_site_id, external_device_id}`` and is upserted
by the explicit ``POST /v2/provider-accounts/{id}/sync-devices`` route. Rows are
never wiped on a provider/sync failure.

This migration is ADDITIVE ONLY: it creates one new table and reuses the
existing ``external_site_sync_status_enum`` (created in
``ff18_telemetry_v2_introduce``); it does not create or alter that enum.

Rollback
--------
``downgrade()`` drops the table (the shared enum is left intact because it is
still used by ``telemetry_external_sites``).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff23_telemetry_external_devices"
down_revision = "ff22_site_mapping_provenance"
branch_labels = None
depends_on = None

EXTERNAL_SITE_SYNC_STATUSES = ("seen", "missing", "stale")


def upgrade() -> None:
    op.create_table(
        "telemetry_external_devices",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "provider_account_id",
            sa.Integer,
            sa.ForeignKey("das_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_site_id", sa.String(255), nullable=False),
        sa.Column("external_device_id", sa.String(255), nullable=False),
        sa.Column("external_device_name", sa.String(512), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB, nullable=True),
        sa.Column("first_seen_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_synced_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_sync_run_id", sa.String(64), nullable=True),
        sa.Column(
            "sync_status",
            postgresql.ENUM(
                *EXTERNAL_SITE_SYNC_STATUSES,
                name="external_site_sync_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'seen'::external_site_sync_status_enum"),
        ),
        sa.Column("last_sync_error", sa.String(1000), nullable=True),
        sa.UniqueConstraint(
            "provider_account_id",
            "external_site_id",
            "external_device_id",
            name="uq_telemetry_external_devices_account_site_device",
        ),
    )
    op.create_index(
        "ix_telemetry_external_devices_account_site",
        "telemetry_external_devices",
        ["provider_account_id", "external_site_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_telemetry_external_devices_account_site",
        table_name="telemetry_external_devices",
    )
    op.drop_table("telemetry_external_devices")
