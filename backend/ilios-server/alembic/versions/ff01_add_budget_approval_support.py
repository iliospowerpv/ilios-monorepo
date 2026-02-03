"""Add budget approval support

Revision ID: ff01_budget_approval
Revises: fea0d415f49b
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

revision = "ff01_budget_approval"
down_revision = "c004a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "finance_approvals",
        sa.Column("budget_id", sa.Integer(), sa.ForeignKey("finance_budgets.id", ondelete="CASCADE"), nullable=True),
    )
    op.alter_column("finance_approvals", "obligation_id", nullable=True)


def downgrade() -> None:
    op.alter_column("finance_approvals", "obligation_id", nullable=False)
    op.drop_column("finance_approvals", "budget_id")
