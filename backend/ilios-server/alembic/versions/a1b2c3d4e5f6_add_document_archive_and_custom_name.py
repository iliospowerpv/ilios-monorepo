"""Add document is_archived and custom_name fields

Revision ID: a1b2c3d4e5f6
Revises: ecaeb0d4307a
Create Date: 2026-01-26 19:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ecaeb0d4307a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('custom_name', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('documents', 'is_archived')
    op.drop_column('documents', 'custom_name')
