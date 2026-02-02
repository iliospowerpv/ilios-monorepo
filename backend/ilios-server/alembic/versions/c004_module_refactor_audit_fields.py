"""Add audit fields to sales_state_transitions

Revision ID: c004a1b2c3d4
Revises: c003a1b2c3d4
Create Date: 2026-02-02

Adds reason and actor_role fields for comprehensive audit trail.
"""

from alembic import op
import sqlalchemy as sa


revision = "c004a1b2c3d4"
down_revision = "c003a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sales_state_transitions",
        sa.Column("reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "sales_state_transitions",
        sa.Column("actor_role", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sales_state_transitions", "actor_role")
    op.drop_column("sales_state_transitions", "reason")
