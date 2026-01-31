"""Add last_test columns for error tracking

Revision ID: b94da896de34
Revises: a85ca895cd23
Create Date: 2026-01-31

Adds last_test_* columns for credential validation tracking.
Existing connections remain with owner_type='company' and owner_company_id=NULL.
"""

from alembic import op
import sqlalchemy as sa


revision = "b94da896de34"
down_revision = "a85ca895cd23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    
    op.add_column(
        "das_connections",
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "das_connections",
        sa.Column("last_test_status", sa.String(20), nullable=True),
    )
    op.add_column(
        "das_connections",
        sa.Column("last_test_message", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("das_connections", "last_test_message")
    op.drop_column("das_connections", "last_test_status")
    op.drop_column("das_connections", "last_test_at")
