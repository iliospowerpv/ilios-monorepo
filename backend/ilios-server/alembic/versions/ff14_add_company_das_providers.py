"""Add company_das_providers association table

Revision ID: ff14_company_das_providers
Revises: ff13_audit_log_indexes
Create Date: 2026-04-13

Adds company_das_providers table to track which telemetry providers
are assigned to each company. Enforces unique constraint on
(company_id, provider) pairs.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff14_company_das_providers"
down_revision = "ff13_audit_log_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    provider_enum = postgresql.ENUM("kmc", "also_energy", name="dasprovidersenum", create_type=False)
    op.create_table(
        "company_das_providers",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column("company_id", sa.Integer, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "provider", name="uq_company_das_provider"),
    )
    op.create_index("ix_company_das_providers_company_id", "company_das_providers", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_company_das_providers_company_id", table_name="company_das_providers")
    op.drop_table("company_das_providers")
