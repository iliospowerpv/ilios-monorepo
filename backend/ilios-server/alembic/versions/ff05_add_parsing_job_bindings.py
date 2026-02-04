"""Add additional parsing job tracking columns

Revision ID: ff05_parsing_job_bindings
Revises: ff04_extraction_registry
Create Date: 2026-02-04

This migration adds additional columns to ai_parsing_results:
- retries, error_message (for error handling)
- is_reprocess, force_reprocess (for reprocess tracking)

Note: document_type_id, schema_version_id, prompt_template_id,
raw_llm_response, parsed_result, extraction_run_number were added in ff04.
"""

import sqlalchemy as sa
from alembic import op


revision = "ff05_parsing_job_bindings"
down_revision = "ff04_extraction_registry"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ai_parsing_results",
        sa.Column("retries", sa.Integer(), nullable=True, server_default="0")
    )
    op.add_column(
        "ai_parsing_results",
        sa.Column("error_message", sa.Text(), nullable=True)
    )
    op.add_column(
        "ai_parsing_results",
        sa.Column("is_reprocess", sa.Boolean(), nullable=True, server_default="false")
    )
    op.add_column(
        "ai_parsing_results",
        sa.Column("force_reprocess", sa.Boolean(), nullable=True, server_default="false")
    )


def downgrade():
    op.drop_column("ai_parsing_results", "force_reprocess")
    op.drop_column("ai_parsing_results", "is_reprocess")
    op.drop_column("ai_parsing_results", "error_message")
    op.drop_column("ai_parsing_results", "retries")
