"""Backfill owner_company_id and add last_test columns

Revision ID: b94da896de34
Revises: a85ca895cd23
Create Date: 2026-01-31

Backfills existing connections with owner_company_id = company_id
and adds last_test_* columns for error tracking.
"""

from alembic import op
import sqlalchemy as sa


revision = "b94da896de34"
down_revision = "a85ca895cd23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE das_connections
        SET owner_company_id = company_id
        WHERE owner_company_id IS NULL
    """)
    
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
