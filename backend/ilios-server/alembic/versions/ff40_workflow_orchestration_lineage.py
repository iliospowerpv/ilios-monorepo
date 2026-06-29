"""Workflow Engine — additive orchestration lineage columns on workflow_runs.

Revision ID: ff40_workflow_orchestration_lineage
Revises: ff39_workflow_engine_foundation
Create Date: 2026-06-29

Background
----------
The Native Onboarding Experience chains otherwise-INDEPENDENT workflow runs (e.g. add a
company, then its first project) into a guided sequence the user can resume across sessions.
To do that durably — without coupling the workflow definitions to each other — this migration
adds three NULLABLE columns to ``workflow_runs``:

* ``parent_run_id`` — self-FK (ON DELETE SET NULL) linking a chained run to the run before it.
* ``sequence_id`` — the declarative SequenceDef id this run participates in (e.g. ``onboarding``).
* ``sequence_step_index`` — which step of that sequence this run fulfils (0-based).

A run is ALWAYS independently startable/executable; these columns are read ONLY by the
orchestrator/dashboard for ordering, resume, and audit lineage — they never change how a
single run executes. Two supporting indexes are added for the dashboard's owner-scoped run
listing and parent lookups.

Hard invariants: additive only — every column is nullable with no default, no existing column
is altered, no data is backfilled, and no operational-truth table is touched.

Rollback
--------
``downgrade()`` drops the two indexes, the self-FK, and the three columns. No pre-existing
object is modified.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ff40_workflow_orchestration_lineage"
down_revision = "ff39_workflow_engine_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_runs", sa.Column("parent_run_id", sa.Integer(), nullable=True))
    op.add_column("workflow_runs", sa.Column("sequence_id", sa.String(), nullable=True))
    op.add_column(
        "workflow_runs", sa.Column("sequence_step_index", sa.Integer(), nullable=True)
    )

    op.create_foreign_key(
        "fk_workflow_runs_parent_run_id",
        "workflow_runs",
        "workflow_runs",
        ["parent_run_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_workflow_runs_parent_run_id", "workflow_runs", ["parent_run_id"]
    )
    op.create_index(
        "ix_workflow_runs_user_sequence_status",
        "workflow_runs",
        ["user_id", "sequence_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_user_sequence_status", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_parent_run_id", table_name="workflow_runs")
    op.drop_constraint(
        "fk_workflow_runs_parent_run_id", "workflow_runs", type_="foreignkey"
    )
    op.drop_column("workflow_runs", "sequence_step_index")
    op.drop_column("workflow_runs", "sequence_id")
    op.drop_column("workflow_runs", "parent_run_id")
