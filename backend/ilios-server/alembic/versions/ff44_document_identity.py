"""Document Identity foundation — additive identity metadata on documents (Task #90).

Revision ID: ff44_document_identity
Revises: ff43_assistant_ui_events
Create Date: 2026-06-30

Background
----------
Formalizes the existing ``documents`` row as the canonical logical *Document Identity*.
This is purely additive metadata layered over the existing Document slot; it changes NO
lifecycle behaviour (promotion / archive / move-stage / versioning) and never creates
placeholder rows.

Two nullable columns are added:

* ``canonical_name`` (VARCHAR, nullable) — the formalized name the business document is
  known by. When set it overrides the resolved display name. Backfilled (light) from the
  existing ``custom_name`` where present so already-renamed documents keep their name as
  their canonical identity; otherwise left NULL so the enum value resolves it.
* ``aliases`` (JSONB, nullable) — optional list of alternate names used by later matching
  phases. Defaults to NULL (treated as an empty list by the model).

Hard invariants: additive only — no existing column is altered or dropped; the canonical
``Site`` entity is untouched.

Rollback
--------
``downgrade()`` drops both added columns. No pre-existing object is touched.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff44_document_identity"
down_revision = "ff43_assistant_ui_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("canonical_name", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("aliases", postgresql.JSONB(), nullable=True))

    # Light backfill: adopt an explicit custom_name as the canonical identity name.
    op.execute(
        "UPDATE documents "
        "SET canonical_name = custom_name "
        "WHERE custom_name IS NOT NULL AND canonical_name IS NULL"
    )


def downgrade() -> None:
    op.drop_column("documents", "aliases")
    op.drop_column("documents", "canonical_name")
