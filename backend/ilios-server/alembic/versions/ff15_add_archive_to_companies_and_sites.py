"""Add archive columns to companies and sites

Revision ID: ff15_archive_companies_sites
Revises: ff14_company_das_providers
Create Date: 2026-04-14

Adds is_archived, archived_at, archived_by columns to both companies
and sites tables. Also adds cascade_archived_by_company to sites.
"""

import sqlalchemy as sa
from alembic import op

revision = "ff15_archive_companies_sites"
down_revision = "ff14_company_das_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.add_column("companies", sa.Column("archived_at", sa.DateTime, nullable=True))
    op.add_column("companies", sa.Column("archived_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_companies_is_archived", "companies", ["is_archived"])

    op.add_column("sites", sa.Column("is_archived", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.add_column("sites", sa.Column("archived_at", sa.DateTime, nullable=True))
    op.add_column("sites", sa.Column("archived_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.add_column("sites", sa.Column("cascade_archived_by_company", sa.Boolean, nullable=False, server_default=sa.text("false")))
    op.create_index("ix_sites_is_archived", "sites", ["is_archived"])


def downgrade() -> None:
    op.drop_index("ix_sites_is_archived", table_name="sites")
    op.drop_column("sites", "cascade_archived_by_company")
    op.drop_column("sites", "archived_by")
    op.drop_column("sites", "archived_at")
    op.drop_column("sites", "is_archived")

    op.drop_index("ix_companies_is_archived", table_name="companies")
    op.drop_column("companies", "archived_by")
    op.drop_column("companies", "archived_at")
    op.drop_column("companies", "is_archived")
