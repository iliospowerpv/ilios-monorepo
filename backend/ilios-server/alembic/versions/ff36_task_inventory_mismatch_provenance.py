"""Additive task provenance columns for "create a tracked task from an inventory gap".

Revision ID: ff36_task_inventory_mismatch_provenance
Revises: ff35_dd_v2_module_specs_specialized_schema
Create Date: 2026-06-24

Background
----------
Task #60 lets a user create a tracked task straight from an actionable device
inventory reconciliation mismatch. Reconciliation itself stays strictly
read-only; the task is created explicitly via a dedicated endpoint.

The ``tasks`` table has no generic metadata/JSON column, so this migration adds
three *nullable, additive* columns that record where a task came from and let us
dedupe open tasks generated from the same reconciliation gap:

* ``source_kind`` — a short discriminator (e.g. ``inventory_reconciliation``).
* ``source_signature`` — the originating mismatch's stable ``mismatch_signature``.
* ``source_context`` — a JSONB provenance snapshot (site id, recommended action,
  device provenance, reconciliation ``generated_at``, etc.).

A composite index on ``(source_kind, source_signature)`` backs the open-task
dedupe lookup. This migration is purely additive: every existing task keeps NULL
for all three columns and nothing else changes.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff36_task_inventory_mismatch_provenance"
down_revision = "ff36_inventory_mismatch_acknowledgements"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("source_kind", sa.String(length=50), nullable=True))
    op.add_column("tasks", sa.Column("source_signature", sa.String(length=255), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("source_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        "ix_tasks_source_kind_signature",
        "tasks",
        ["source_kind", "source_signature"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_source_kind_signature", table_name="tasks")
    op.drop_column("tasks", "source_context")
    op.drop_column("tasks", "source_signature")
    op.drop_column("tasks", "source_kind")
