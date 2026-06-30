"""Data Room Templates — reusable, company-scoped structure snapshots (Task #91).

Revision ID: ff45_data_room_templates
Revises: ff44_document_identity
Create Date: 2026-06-30

Background
----------
Adds a single additive table, ``data_room_templates``, that stores a reusable
snapshot of a Data Room's *structure* (stages/sections, expected documents,
ordering, descriptions, guidance, optionality) as an enum-anchored JSON blob.

A template is company-scoped and is consumed by the existing site-creation path
to scaffold a new Data Room. It never stores files, versions, metadata/keys,
approvals or history, and applying it never creates placeholder File rows.

Hard invariants: additive only — no existing table or column is altered or
dropped; the canonical ``Site`` entity is untouched.

Rollback
--------
``downgrade()`` drops the table. No pre-existing object is touched.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff45_data_room_templates"
down_revision = "ff44_document_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_room_templates",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("structure", postgresql.JSONB(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_room_templates_company",
        "data_room_templates",
        ["company_id", "is_archived"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_data_room_templates_company", table_name="data_room_templates")
    op.drop_table("data_room_templates")
