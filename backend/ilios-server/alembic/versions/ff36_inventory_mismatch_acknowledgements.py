"""Inventory Reconciliation reviewer acknowledgements (Phase B).

Adds the first governed write path for Device Inventory Reconciliation: a single
additive table ``inventory_mismatch_acknowledgements`` (plus one Postgres enum
type) that records a reviewer's "checked, acceptable exception" decision against
an EXACT ``(site_id, mismatch_signature, reconciliation_version)`` triple.

This migration is ADDITIVE ONLY. It does not touch ``devices``,
``telemetry_devices_mapping`` / ``telemetry_sites_mapping``, ``project_facts``,
``telemetry_*``, ``weather_device_mappings``, baselines, or any existing enum.
No external provider, secret, BigQuery, or Firestore concern is introduced.

A partial unique index guarantees at most one ACTIVE acknowledgement per triple
while retaining revoked rows as immutable history. ``downgrade()`` drops the
table then the enum type.

Revision ID: ff36_inventory_mismatch_acknowledgements
Revises: ff37_weather_declaration_single_active
Create Date: 2026-06-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff36_inventory_mismatch_acknowledgements"
down_revision = "ff37_weather_declaration_single_active"
branch_labels = None
depends_on = None

ACK_STATUS_ENUM_NAME = "inventory_ack_status_enum"
ACK_STATUSES = ("acknowledged", "revoked")


def _enum(name, values) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    _enum(ACK_STATUS_ENUM_NAME, ACK_STATUSES).create(bind, checkfirst=True)

    op.create_table(
        "inventory_mismatch_acknowledgements",
        sa.Column(
            "id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True
        ),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mismatch_signature", sa.String(512), nullable=False),
        sa.Column("reconciliation_version", sa.String(64), nullable=False),
        sa.Column("mismatch_type", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(64), nullable=False),
        sa.Column("acknowledgement_policy", sa.String(64), nullable=False),
        sa.Column("mismatch_title", sa.Text, nullable=False),
        sa.Column("mismatch_detail", sa.Text, nullable=True),
        sa.Column("source_module", sa.String(128), nullable=True),
        sa.Column("source_context", postgresql.JSONB, nullable=True),
        sa.Column("acknowledged_context_hash", sa.String(64), nullable=True),
        sa.Column(
            "status",
            _enum(ACK_STATUS_ENUM_NAME, ACK_STATUSES),
            nullable=False,
            server_default=sa.text(f"'acknowledged'::{ACK_STATUS_ENUM_NAME}"),
        ),
        sa.Column(
            "acknowledged_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "acknowledged_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("acknowledgement_reason", sa.Text, nullable=False),
        sa.Column(
            "revoked_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
        sa.Column("revocation_reason", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_inv_mismatch_ack_site_status",
        "inventory_mismatch_acknowledgements",
        ["site_id", "status"],
    )
    op.create_index(
        "ix_inv_mismatch_ack_signature",
        "inventory_mismatch_acknowledgements",
        ["site_id", "mismatch_signature", "reconciliation_version"],
    )
    op.create_index(
        "uq_inv_mismatch_ack_active",
        "inventory_mismatch_acknowledgements",
        ["site_id", "mismatch_signature", "reconciliation_version"],
        unique=True,
        postgresql_where=sa.text("status = 'acknowledged'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_inv_mismatch_ack_active",
        table_name="inventory_mismatch_acknowledgements",
    )
    op.drop_index(
        "ix_inv_mismatch_ack_signature",
        table_name="inventory_mismatch_acknowledgements",
    )
    op.drop_index(
        "ix_inv_mismatch_ack_site_status",
        table_name="inventory_mismatch_acknowledgements",
    )
    op.drop_table("inventory_mismatch_acknowledgements")
    _enum(ACK_STATUS_ENUM_NAME, ACK_STATUSES).drop(op.get_bind(), checkfirst=True)
