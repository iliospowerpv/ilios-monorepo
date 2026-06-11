"""DD V2 Phase 1A: additive provenance/audit columns on project_facts + document_keys.override_notes.

Revision ID: ff29_dd_v2_fact_provenance
Revises: ff28_telemetry_expected_baselines
Create Date: 2026-06-11

Background
----------
Phase 1A of the Due Diligence V2 upgrade. Adds nullable, additive provenance and
audit columns to ``project_facts`` so a candidate/promoted fact is an immutable,
fully-traceable snapshot of the evidence and reviewer actions behind it:

* ``superseded_by_fact_id`` — forward-semantics reverse pointer (the retired fact
  points at the new fact that superseded it). ``supersedes_fact_id`` is left
  untouched for backward compatibility with summary_stats.py.
* ``evidence`` (JSONB) — {page, snippet, anchor_text} copied from the parse run.
* ``ai_confidence`` (Float) and ``ai_extracted_value`` (JSONB) — the raw model
  output, retained so a human override never loses the original AI value.
* ``accepted_by_id`` / ``accepted_at`` / ``overridden_by_id`` / ``overridden_at`` /
  ``override_notes`` — reviewer identity + rationale snapshot.
* ``effective_from`` / ``effective_to`` — activation window for an active fact.
* ``source_document_type`` — the DD document type the fact was sourced from.

It also adds ``document_keys.override_notes`` (Phase 1D guardrail) — the reviewer
rationale captured when a baseline-driving key is overridden.

All columns are NULLABLE with no non-null default, so existing rows are untouched
and null provenance never breaks existing reads. This migration is ADDITIVE ONLY:
it adds columns plus three new foreign keys; it does not alter or drop any existing
column, constraint, table, or enum.

Rollback
--------
``downgrade()`` drops exactly the columns/constraints added here.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff29_dd_v2_fact_provenance"
down_revision = "ff28_telemetry_expected_baselines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("project_facts", sa.Column("superseded_by_fact_id", sa.Integer(), nullable=True))
    op.add_column("project_facts", sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("project_facts", sa.Column("ai_confidence", sa.Float(), nullable=True))
    op.add_column("project_facts", sa.Column("ai_extracted_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("project_facts", sa.Column("accepted_by_id", sa.Integer(), nullable=True))
    op.add_column("project_facts", sa.Column("accepted_at", sa.DateTime(), nullable=True))
    op.add_column("project_facts", sa.Column("overridden_by_id", sa.Integer(), nullable=True))
    op.add_column("project_facts", sa.Column("overridden_at", sa.DateTime(), nullable=True))
    op.add_column("project_facts", sa.Column("override_notes", sa.Text(), nullable=True))
    op.add_column("project_facts", sa.Column("effective_from", sa.DateTime(), nullable=True))
    op.add_column("project_facts", sa.Column("effective_to", sa.DateTime(), nullable=True))
    op.add_column("project_facts", sa.Column("source_document_type", sa.String(length=255), nullable=True))

    op.create_foreign_key(
        "fk_project_facts_superseded_by_fact",
        "project_facts", "project_facts",
        ["superseded_by_fact_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_project_facts_accepted_by",
        "project_facts", "users",
        ["accepted_by_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_project_facts_overridden_by",
        "project_facts", "users",
        ["overridden_by_id"], ["id"],
        ondelete="SET NULL",
    )

    op.add_column("document_keys", sa.Column("override_notes", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_keys", "override_notes")

    op.drop_constraint("fk_project_facts_overridden_by", "project_facts", type_="foreignkey")
    op.drop_constraint("fk_project_facts_accepted_by", "project_facts", type_="foreignkey")
    op.drop_constraint("fk_project_facts_superseded_by_fact", "project_facts", type_="foreignkey")

    for col in (
        "source_document_type",
        "effective_to",
        "effective_from",
        "override_notes",
        "overridden_at",
        "overridden_by_id",
        "accepted_at",
        "accepted_by_id",
        "ai_extracted_value",
        "ai_confidence",
        "evidence",
        "superseded_by_fact_id",
    ):
        op.drop_column("project_facts", col)
