"""Add performance indexes to audit_logs table

Revision ID: ff13_audit_log_indexes
Revises: ff12_entity_directory
Create Date: 2026-03-16

Adds:
1. ix_audit_logs_created_at — DESC index on created_at for ORDER BY
2. ix_audit_logs_user_id — index on user_id FK for the outerjoin
"""

import sqlalchemy as sa
from alembic import op

revision = "ff13_audit_log_indexes"
down_revision = "ff12_entity_directory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_audit_logs_created_at",
        "audit_logs",
        [sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_user_id",
        "audit_logs",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
