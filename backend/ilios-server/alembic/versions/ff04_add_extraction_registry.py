"""Add extraction registry tables

Revision ID: ff04_extraction_registry
Revises: ff03_document_versioning
Create Date: 2026-02-04

This migration adds the Extraction Registry system:
- extraction_document_types: Registry of parsable document types
- extraction_schema_versions: Versioned field schemas per document type
- extraction_schema_version_fields: Junction table for schema-field relationships
- extraction_prompt_templates: Versioned prompt templates per document type
- Updates to document_parse_jobs for registry binding
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "ff04_extraction_registry"
down_revision = "ff03_document_versioning"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "extraction_document_types",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False, server_default="other"),
        sa.Column("is_parsable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_extraction_document_types_name", "extraction_document_types", ["name"])
    op.create_index("ix_extraction_document_types_active", "extraction_document_types", ["is_active"])

    op.create_table(
        "extraction_schema_versions",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("document_type_id", sa.Integer(), sa.ForeignKey("extraction_document_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_extraction_schema_versions_doc_type", "extraction_schema_versions", ["document_type_id"])
    op.create_index(
        "ix_extraction_schema_versions_active_unique",
        "extraction_schema_versions",
        ["document_type_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true")
    )

    op.create_table(
        "extraction_schema_version_fields",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("schema_version_id", sa.Integer(), sa.ForeignKey("extraction_schema_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_field_id", sa.Integer(), sa.ForeignKey("canonical_fields.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extraction_priority", sa.Integer(), nullable=False, server_default="100"),
        sa.UniqueConstraint("schema_version_id", "canonical_field_id", name="uq_schema_version_field"),
    )
    op.create_index("ix_schema_version_fields_schema", "extraction_schema_version_fields", ["schema_version_id"])
    op.create_index("ix_schema_version_fields_field", "extraction_schema_version_fields", ["canonical_field_id"])

    op.create_table(
        "extraction_prompt_templates",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("document_type_id", sa.Integer(), sa.ForeignKey("extraction_document_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("extraction_prompt", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False, server_default="claude-sonnet-4-5"),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="8000"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_extraction_prompt_templates_doc_type", "extraction_prompt_templates", ["document_type_id"])
    op.create_index(
        "ix_extraction_prompt_templates_active_unique",
        "extraction_prompt_templates",
        ["document_type_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true")
    )

    op.add_column("ai_parsing_results", sa.Column("document_type_id", sa.Integer(), nullable=True))
    op.add_column("ai_parsing_results", sa.Column("schema_version_id", sa.Integer(), nullable=True))
    op.add_column("ai_parsing_results", sa.Column("prompt_template_id", sa.Integer(), nullable=True))
    op.add_column("ai_parsing_results", sa.Column("raw_llm_response", sa.Text(), nullable=True))
    op.add_column("ai_parsing_results", sa.Column("parsed_result", postgresql.JSONB(), nullable=True))
    op.add_column("ai_parsing_results", sa.Column("extraction_run_number", sa.Integer(), nullable=True, server_default="1"))

    op.create_foreign_key(
        "fk_ai_parsing_results_document_type",
        "ai_parsing_results",
        "extraction_document_types",
        ["document_type_id"],
        ["id"],
        ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_ai_parsing_results_schema_version",
        "ai_parsing_results",
        "extraction_schema_versions",
        ["schema_version_id"],
        ["id"],
        ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_ai_parsing_results_prompt_template",
        "ai_parsing_results",
        "extraction_prompt_templates",
        ["prompt_template_id"],
        ["id"],
        ondelete="SET NULL"
    )


def downgrade():
    op.drop_constraint("fk_ai_parsing_results_prompt_template", "ai_parsing_results", type_="foreignkey")
    op.drop_constraint("fk_ai_parsing_results_schema_version", "ai_parsing_results", type_="foreignkey")
    op.drop_constraint("fk_ai_parsing_results_document_type", "ai_parsing_results", type_="foreignkey")
    op.drop_column("ai_parsing_results", "extraction_run_number")
    op.drop_column("ai_parsing_results", "parsed_result")
    op.drop_column("ai_parsing_results", "raw_llm_response")
    op.drop_column("ai_parsing_results", "prompt_template_id")
    op.drop_column("ai_parsing_results", "schema_version_id")
    op.drop_column("ai_parsing_results", "document_type_id")

    op.drop_table("extraction_prompt_templates")
    op.drop_table("extraction_schema_version_fields")
    op.drop_table("extraction_schema_versions")
    op.drop_table("extraction_document_types")
