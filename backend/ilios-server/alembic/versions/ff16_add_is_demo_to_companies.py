"""Add is_demo flag to companies

Revision ID: ff16_add_is_demo_to_companies
Revises: ff15_archive_companies_sites
Create Date: 2026-04-15

Adds is_demo boolean column to companies table to identify demo companies
whose projects should use simulated telemetry data.
"""

import sqlalchemy as sa
from alembic import op

revision = "ff16_add_is_demo_to_companies"
down_revision = "ff15_archive_companies_sites"
branch_labels = None
depends_on = None

DEMO_COMPANY_ID = 15


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "is_demo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        sa.text(
            "UPDATE companies SET is_demo = true WHERE id = :cid"
        ).bindparams(cid=DEMO_COMPANY_ID)
    )


def downgrade() -> None:
    op.drop_column("companies", "is_demo")
