"""add_unique_constraint_converted_project_id

Revision ID: ecaeb0d4307a
Revises: aa97f8f2cb84
Create Date: 2026-01-26 17:30:43.791919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecaeb0d4307a'
down_revision: Union[str, None] = 'aa97f8f2cb84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint on converted_to_project_id to prevent duplicate conversions
    # This ensures one-to-one mapping between deals and sites
    op.create_unique_constraint(
        'uq_deals_converted_to_project_id',
        'deals',
        ['converted_to_project_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_deals_converted_to_project_id', 'deals', type_='unique')
