"""Weather Semantics Governed Declaration (WS.1) — governance layer + append-only guard.

Revision ID: ff36_weather_semantics_governed_declaration
Revises: ff35_dd_v2_module_specs_specialized_schema
Create Date: 2026-06-22

Background
----------
Layer-1 governance for ``weather_device_mappings`` (see
``app/models/weather.py`` and ``app/db/weather_declaration_guard.py``). This
migration is ADDITIVE ONLY and changes no existing behavior at deploy:

* Two new Postgres enum types: ``weather_declaration_basis_enum`` and
  ``weather_declaration_status_enum`` (draft/active/superseded — ``needs_re_review``
  is a boolean flag, NOT a status).
* The existing approval ledger enums gain values: target ``weather_device_mapping``
  and actions ``declare_draft`` / ``activate`` / ``needs_re_review``
  (``supersede`` already exists). Added with ``ADD VALUE IF NOT EXISTS`` and NOT
  used within this migration's transaction (precedent: ff07).
* ~18 additive NULLable governance columns on ``weather_device_mappings`` (no
  value-mutating server default) plus two resolution indexes.
* A ``BEFORE UPDATE`` PL/pgSQL append-only trigger (governed rows only; legacy
  NULL-status rows exempt; INSERT unaffected). The canonical SQL lives in
  ``app/db/weather_declaration_guard.py`` and is imported here so the trigger,
  the ORM guard, and the pytest fixture stay byte-identical.

Chained off the current single alembic head (``ff35``) so ``upgrade head`` stays
linear and clean. Nothing here writes ``expected_weather_provenance``, touches the
resolver/expected math, ingestion, rollups, the scheduler, device
eligibility/classification, baselines, or O&M.

Rollback
--------
``downgrade()`` drops the trigger + function, the two resolution indexes, the 18
columns, and the two NEW enum types. It intentionally LEAVES the added
approval-ledger enum labels in place: PostgreSQL cannot drop a single enum value,
and the labels are harmless/forward-compatible (re-running upgrade re-adds them
idempotently).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.db.weather_declaration_guard import APPLY_GUARD_SQL, REMOVE_GUARD_SQL

revision = "ff36_weather_semantics_governed_declaration"
down_revision = "ff35_dd_v2_module_specs_specialized_schema"
branch_labels = None
depends_on = None


# Enum type names (kept in lockstep with app/models/weather.py).
DECLARATION_BASIS_ENUM_NAME = "weather_declaration_basis_enum"
DECLARATION_STATUS_ENUM_NAME = "weather_declaration_status_enum"
APPROVAL_TARGET_TYPE_ENUM_NAME = "weather_approval_target_type_enum"
APPROVAL_ACTION_ENUM_NAME = "weather_approval_action_enum"

DECLARATION_BASES = (
    "provider_confirmed",
    "source_document",
    "reviewer_source_note",
    "reviewer_assumption",
)
DECLARATION_STATUSES = ("draft", "active", "superseded")

# Additive values for the existing approval-ledger enums.
APPROVAL_TARGET_TYPE_ADDED = ("weather_device_mapping",)
APPROVAL_ACTION_ADDED = ("declare_draft", "activate", "needs_re_review")

TABLE = "weather_device_mappings"


def _enum(name, values):
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # ------------------------------------------------------------------
    # 1. New enum types (created once; columns reference create_type=False).
    # ------------------------------------------------------------------
    _enum(DECLARATION_BASIS_ENUM_NAME, DECLARATION_BASES).create(bind, checkfirst=True)
    _enum(DECLARATION_STATUS_ENUM_NAME, DECLARATION_STATUSES).create(
        bind, checkfirst=True
    )

    # ------------------------------------------------------------------
    # 2. Extend the existing approval-ledger enums (idempotent; not used in
    #    this transaction). PostgreSQL forbids using a freshly added enum
    #    value in the same transaction, so these are additions only.
    # ------------------------------------------------------------------
    for value in APPROVAL_TARGET_TYPE_ADDED:
        op.execute(
            f"ALTER TYPE {APPROVAL_TARGET_TYPE_ENUM_NAME} "
            f"ADD VALUE IF NOT EXISTS '{value}'"
        )
    for value in APPROVAL_ACTION_ADDED:
        op.execute(
            f"ALTER TYPE {APPROVAL_ACTION_ENUM_NAME} "
            f"ADD VALUE IF NOT EXISTS '{value}'"
        )

    # ------------------------------------------------------------------
    # 3. Additive NULLable governance columns (no value-mutating defaults).
    # ------------------------------------------------------------------
    op.add_column(
        TABLE,
        sa.Column(
            "declaration_status",
            _enum(DECLARATION_STATUS_ENUM_NAME, DECLARATION_STATUSES),
            nullable=True,
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "declaration_basis",
            _enum(DECLARATION_BASIS_ENUM_NAME, DECLARATION_BASES),
            nullable=True,
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "source_document_id",
            sa.Integer,
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "source_file_id",
            sa.Integer,
            sa.ForeignKey("files.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(TABLE, sa.Column("reviewer_note", sa.Text, nullable=True))
    op.add_column(TABLE, sa.Column("sensor_role", sa.String(128), nullable=True))
    op.add_column(TABLE, sa.Column("sensor_model", sa.String(255), nullable=True))
    op.add_column(
        TABLE, sa.Column("provider_metadata_json", postgresql.JSONB, nullable=True)
    )
    op.add_column(
        TABLE, sa.Column("upstream_fingerprint_json", postgresql.JSONB, nullable=True)
    )
    op.add_column(
        TABLE,
        sa.Column(
            "declared_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(TABLE, sa.Column("declared_at", sa.DateTime, nullable=True))
    op.add_column(
        TABLE,
        sa.Column(
            "activated_by",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(TABLE, sa.Column("activated_at", sa.DateTime, nullable=True))
    op.add_column(
        TABLE,
        sa.Column(
            "supersedes_mapping_id",
            sa.Integer,
            sa.ForeignKey("weather_device_mappings.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "superseded_by_mapping_id",
            sa.Integer,
            sa.ForeignKey("weather_device_mappings.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(TABLE, sa.Column("needs_re_review", sa.Boolean, nullable=True))
    op.add_column(TABLE, sa.Column("re_review_reason", sa.Text, nullable=True))
    op.add_column(
        TABLE, sa.Column("eligibility_snapshot_json", postgresql.JSONB, nullable=True)
    )

    # ------------------------------------------------------------------
    # 4. Resolution indexes for current-declaration lookup by status.
    # ------------------------------------------------------------------
    op.create_index(
        "ix_weather_device_mappings_declaration",
        TABLE,
        ["device_id", "metric", "declaration_status"],
    )
    op.create_index(
        "ix_weather_device_mappings_decl_status", TABLE, ["declaration_status"]
    )

    # ------------------------------------------------------------------
    # 5. Append-only DB trigger (governed rows only; canonical SQL imported).
    # ------------------------------------------------------------------
    for statement in APPLY_GUARD_SQL:
        op.execute(statement)


def downgrade() -> None:
    bind = op.get_bind()

    # 5. Remove the trigger + function first.
    for statement in REMOVE_GUARD_SQL:
        op.execute(statement)

    # 4. Drop the resolution indexes.
    op.drop_index("ix_weather_device_mappings_decl_status", table_name=TABLE)
    op.drop_index("ix_weather_device_mappings_declaration", table_name=TABLE)

    # 3. Drop the governance columns (reverse order of creation).
    for column in (
        "eligibility_snapshot_json",
        "re_review_reason",
        "needs_re_review",
        "superseded_by_mapping_id",
        "supersedes_mapping_id",
        "activated_at",
        "activated_by",
        "declared_at",
        "declared_by",
        "upstream_fingerprint_json",
        "provider_metadata_json",
        "sensor_model",
        "sensor_role",
        "reviewer_note",
        "source_file_id",
        "source_document_id",
        "declaration_basis",
        "declaration_status",
    ):
        op.drop_column(TABLE, column)

    # 1. Drop the two NEW enum types. The approval-ledger enum values added in
    #    step 2 are intentionally LEFT in place — PostgreSQL cannot drop a single
    #    enum label, and the extra labels are forward-compatible no-ops.
    _enum(DECLARATION_STATUS_ENUM_NAME, DECLARATION_STATUSES).drop(bind, checkfirst=True)
    _enum(DECLARATION_BASIS_ENUM_NAME, DECLARATION_BASES).drop(bind, checkfirst=True)
