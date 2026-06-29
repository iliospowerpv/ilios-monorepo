"""Native Workflow Engine & Wizard Framework foundation — additive run/step tables.

Revision ID: ff39_workflow_engine_foundation
Revises: ff38_weather_provider_framework
Create Date: 2026-06-29

Background
----------
Adds the two tables that back the native Workflow Engine. They persist ONLY the progress of a
guided wizard run — never business truth. Operational truth keeps flowing through the existing
domain tables/endpoints; these tables track collected inputs, validation/execution state, and
links (by id) to the domain entity + audit row that an executed write step produced via an
EXISTING endpoint.

* ``workflow_runs`` — one in-progress/completed run of a workflow definition for a single
  user. Binds (workflow_id, workflow_version) so a resumed run can be re-validated. Optional
  company_id/site_id scope (null when the run itself creates the scoping entity, e.g.
  add_company). ``resume_token`` is unique.
* ``workflow_step_states`` — per-step collected inputs (JSONB), server validation state, and
  for a write step the ``executed`` flag + ``idempotency_key`` (prevent double execution) plus
  ``result_entity_type/result_entity_id`` and ``audit_log_id`` (link to what the existing
  endpoint produced). Unique on (run_id, step_id) and on idempotency_key.

Hard invariants: additive only — NO existing table is modified; foreign keys reference
``users``/``companies``/``sites``/``audit_logs`` with safe ON DELETE (SET NULL, except the
run->step CASCADE). No operational-truth column is touched.

Rollback
--------
``downgrade()`` drops the two tables (and their indexes/constraints) then the two enum types.
No pre-existing object is touched.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff39_workflow_engine_foundation"
down_revision = "ff38_weather_provider_framework"
branch_labels = None
depends_on = None


# Enum type names (kept in lockstep with app/models/workflow.py).
WORKFLOW_RUN_STATUS_ENUM_NAME = "workflow_run_status_enum"
WORKFLOW_STEP_STATUS_ENUM_NAME = "workflow_step_status_enum"

WORKFLOW_RUN_STATUSES = ("active", "paused", "completed", "abandoned")
WORKFLOW_STEP_STATUSES = ("pending", "valid", "invalid")


def _enum(name, values):
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # Enum types (created once; columns reference them with create_type=False)
    # ------------------------------------------------------------------
    _enum(WORKFLOW_RUN_STATUS_ENUM_NAME, WORKFLOW_RUN_STATUSES).create(bind, checkfirst=True)
    _enum(WORKFLOW_STEP_STATUS_ENUM_NAME, WORKFLOW_STEP_STATUSES).create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # 1. workflow_runs
    # ------------------------------------------------------------------
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("workflow_id", sa.String(), nullable=False),
        sa.Column("workflow_version", sa.String(), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "site_id",
            sa.Integer,
            sa.ForeignKey("sites.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            _enum(WORKFLOW_RUN_STATUS_ENUM_NAME, WORKFLOW_RUN_STATUSES),
            nullable=False,
            server_default=sa.text(f"'active'::{WORKFLOW_RUN_STATUS_ENUM_NAME}"),
        ),
        sa.Column("current_step", sa.String(), nullable=True),
        sa.Column("resume_token", sa.String(), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_runs_user_id", "workflow_runs", ["user_id"])
    op.create_index("ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"])
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"])

    # ------------------------------------------------------------------
    # 2. workflow_step_states
    # ------------------------------------------------------------------
    op.create_table(
        "workflow_step_states",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer,
            sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_id", sa.String(), nullable=False),
        sa.Column("inputs", postgresql.JSONB, nullable=True),
        sa.Column(
            "validation_status",
            _enum(WORKFLOW_STEP_STATUS_ENUM_NAME, WORKFLOW_STEP_STATUSES),
            nullable=False,
            server_default=sa.text(f"'pending'::{WORKFLOW_STEP_STATUS_ENUM_NAME}"),
        ),
        sa.Column("validation_errors", postgresql.JSONB, nullable=True),
        sa.Column(
            "executed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("result_entity_type", sa.String(), nullable=True),
        sa.Column("result_entity_id", sa.Integer, nullable=True),
        sa.Column(
            "audit_log_id",
            sa.Integer,
            sa.ForeignKey("audit_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("run_id", "step_id", name="uq_workflow_step_states_run_id_step_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_workflow_step_states_idempotency_key"),
    )
    op.create_index("ix_workflow_step_states_run_id", "workflow_step_states", ["run_id"])


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_workflow_step_states_run_id", table_name="workflow_step_states")
    op.drop_table("workflow_step_states")

    op.drop_index("ix_workflow_runs_status", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_workflow_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_user_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")

    _enum(WORKFLOW_STEP_STATUS_ENUM_NAME, WORKFLOW_STEP_STATUSES).drop(bind, checkfirst=True)
    _enum(WORKFLOW_RUN_STATUS_ENUM_NAME, WORKFLOW_RUN_STATUSES).drop(bind, checkfirst=True)
