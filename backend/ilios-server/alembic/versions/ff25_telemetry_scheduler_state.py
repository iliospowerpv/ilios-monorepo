"""Native V2 telemetry scheduler state.

Revision ID: ff25_telemetry_scheduler_state
Revises: ff24_telemetry_native_ingestion
Create Date: 2026-06-10

Background
----------
Adds the durable scheduling/automation layer for native V2 telemetry. The
scheduler runner and the bounded backfill endpoint both reuse the *same*
ingestion + rollup services as the manual Refresh Telemetry action — they are
simply new triggers (``scheduled`` / ``backfill``, already present on
``telemetry_sync_trigger_enum``). This table only carries scheduling metadata
and a DB-backed lease lock so overlapping runs for the same site cannot start.

``telemetry_scheduler_state`` — one row per (``site_id``, ``provider_account_id``):

* ``enabled`` / ``cadence`` — automation flag + ISO-8601 duration from a fixed
  whitelist (PT15M/PT30M/PT1H/PT6H/PT24H, enforced in the API, not the schema).
* ``last_run_at`` / ``last_successful_pull_at`` / ``last_status`` / ``last_error``
  / ``last_sync_job_id`` — health + the scheduled cursor. ``last_status`` is a
  free string (not the sync-status enum) so it can also hold ``config_error``
  (raised before any sync job exists) and ``skipped``.
* ``next_due_at`` — when the runner should next consider this row.
* ``lock_token`` / ``locked_until`` — lease-based claim for overlap prevention; a
  crashed run's lease self-expires so the row is reclaimable.

Rows are created lazily on the first enable/backfill — there is intentionally
NO seed here, so site mappings created after this migration get the same lazy
path with no schema change.

This migration is ADDITIVE ONLY. It does not touch the ``sites`` table or any
existing telemetry table/enum, and it introduces no new enum types.

Rollback
--------
``downgrade()`` drops the table (and its indexes).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ff25_telemetry_scheduler_state"
down_revision = "ff24_telemetry_native_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telemetry_scheduler_state",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider_account_id",
            sa.Integer,
            sa.ForeignKey("das_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "enabled", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "cadence", sa.String(16), nullable=False, server_default=sa.text("'PT1H'")
        ),
        sa.Column("last_run_at", sa.DateTime, nullable=True),
        sa.Column("last_successful_pull_at", sa.DateTime, nullable=True),
        sa.Column("last_status", sa.String(16), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "last_sync_job_id",
            sa.Integer,
            sa.ForeignKey("telemetry_sync_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("next_due_at", sa.DateTime, nullable=True),
        sa.Column("lock_token", sa.String(64), nullable=True),
        sa.Column("locked_until", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "site_id",
            "provider_account_id",
            name="uq_telemetry_scheduler_state_site_account",
        ),
    )
    op.create_index(
        "ix_telemetry_scheduler_state_due",
        "telemetry_scheduler_state",
        ["enabled", "next_due_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_telemetry_scheduler_state_due",
        table_name="telemetry_scheduler_state",
    )
    op.drop_table("telemetry_scheduler_state")
