"""Add document versioning, project facts, and assumptions promotions

Revision ID: ff03_document_versioning
Revises: ff02_add_role_profiles
Create Date: 2026-02-04

This migration adds:
1. canonical_fields table - field definitions for extraction
2. file_id column on document_keys - scope keys to specific versions
3. project_facts table - lender-quality assumptions (candidate/active/retired)
4. assumptions_promotions table - audit trail for promotions
5. Version metadata columns on files table

This implements lender-quality Data Room versioning with:
- Multiple file versions per document series
- Version-scoped key acceptance
- Explicit "Promote to Current Assumptions" workflow
- Full audit trail for compliance
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "ff03_document_versioning"
down_revision: Union[str, None] = "ff02_add_role_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canonical_fields",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("field_type", sa.String(50), nullable=False, server_default="text"),
        sa.Column("validation_regex", sa.String(500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_canonical_fields_name", "canonical_fields", ["name"], unique=True)

    op.add_column(
        "files",
        sa.Column("version_number", sa.Integer(), nullable=True)
    )
    op.add_column(
        "files",
        sa.Column("version_label", sa.String(100), nullable=True)
    )
    op.add_column(
        "files",
        sa.Column("change_notes", sa.Text(), nullable=True)
    )
    op.add_column(
        "files",
        sa.Column("storage_key", sa.String(500), nullable=True)
    )

    op.drop_constraint("_document_key_uc", "document_keys", type_="unique")
    op.drop_index("ix_document_key_name", table_name="document_keys")

    op.add_column(
        "document_keys",
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    )

    op.create_unique_constraint(
        "_document_key_version_uc",
        "document_keys",
        ["document_id", "file_id", "name"]
    )
    op.create_index(
        "ix_document_key_version_name",
        "document_keys",
        ["document_id", "file_id", "name"],
        unique=True
    )

    op.create_table(
        "project_facts",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_field_id", sa.Integer(), sa.ForeignKey("canonical_fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", JSONB(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="candidate"),
        sa.Column("source_file_id", sa.Integer(), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=True),
        sa.Column("source_document_key_id", sa.Integer(), sa.ForeignKey("document_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("promoted_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("promoted_at", sa.DateTime(), nullable=True),
        sa.Column("promotion_notes", sa.Text(), nullable=True),
        sa.Column("supersedes_fact_id", sa.Integer(), sa.ForeignKey("project_facts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_index(
        "ix_project_facts_site_field",
        "project_facts",
        ["site_id", "canonical_field_id"]
    )
    op.create_index(
        "ix_project_facts_active_unique",
        "project_facts",
        ["site_id", "canonical_field_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'")
    )
    op.create_index(
        "ix_project_facts_status",
        "project_facts",
        ["status"]
    )
    op.create_index(
        "ix_project_facts_source_file",
        "project_facts",
        ["source_file_id"]
    )

    op.create_table(
        "assumptions_promotions",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("site_id", sa.Integer(), sa.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", sa.Integer(), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("promoted_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("promoted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("diff_json", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_assumptions_promotions_site",
        "assumptions_promotions",
        ["site_id"]
    )
    op.create_index(
        "ix_assumptions_promotions_file",
        "assumptions_promotions",
        ["file_id"]
    )
    op.create_index(
        "ix_assumptions_promotions_promoted_at",
        "assumptions_promotions",
        ["promoted_at"]
    )


def downgrade() -> None:
    op.drop_table("assumptions_promotions")

    op.drop_index("ix_project_facts_source_file", table_name="project_facts")
    op.drop_index("ix_project_facts_status", table_name="project_facts")
    op.drop_index("ix_project_facts_active_unique", table_name="project_facts")
    op.drop_index("ix_project_facts_site_field", table_name="project_facts")
    op.drop_table("project_facts")

    op.drop_constraint("_document_key_version_uc", "document_keys", type_="unique")
    op.drop_index("ix_document_key_version_name", table_name="document_keys")
    op.drop_column("document_keys", "file_id")

    op.create_unique_constraint("_document_key_uc", "document_keys", ["document_id", "name"])
    op.create_index("ix_document_key_name", "document_keys", ["document_id", "name"], unique=True)

    op.drop_column("files", "storage_key")
    op.drop_column("files", "change_notes")
    op.drop_column("files", "version_label")
    op.drop_column("files", "version_number")

    op.drop_index("ix_canonical_fields_name", table_name="canonical_fields")
    op.drop_table("canonical_fields")
