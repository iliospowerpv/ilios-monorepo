"""Add DAS connection dual ownership columns

Revision ID: a85ca895cd23
Revises: cef043dc598b
Create Date: 2026-01-31

This migration adds support for portfolio-level DAS connection ownership.
Connections can be owned by either a company (existing behavior) or a portfolio hub.
"""

from alembic import op
import sqlalchemy as sa


revision = "a85ca895cd23"
down_revision = "cef043dc598b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "das_connections",
        sa.Column(
            "owner_type",
            sa.String(20),
            nullable=False,
            server_default="company",
        ),
    )
    op.create_check_constraint(
        "ck_das_connections_owner_type",
        "das_connections",
        "owner_type IN ('company', 'portfolio')",
    )
    
    op.add_column(
        "das_connections",
        sa.Column(
            "owner_company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    
    op.create_index(
        "idx_das_connections_owner",
        "das_connections",
        ["owner_type", "owner_company_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_das_connections_owner", table_name="das_connections")
    op.drop_constraint("ck_das_connections_owner_type", "das_connections", type_="check")
    op.drop_column("das_connections", "owner_company_id")
    op.drop_column("das_connections", "owner_type")
