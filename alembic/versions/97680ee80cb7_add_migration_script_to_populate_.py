"""Add migration script to populate default roles in DB

Revision ID: 97680ee80cb7
Revises: 57f149af3c1e
Create Date: 2024-02-16 16:17:42.610464

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.helpers.default_roles_helper import DefaultRolesHelper

# revision identifiers, used by Alembic.
revision: str = '97680ee80cb7'
down_revision: Union[str, None] = '57f149af3c1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # New roles are updated in migration 484b5758cf6d
    pass


def downgrade() -> None:
    # New roles are updated in migration 484b5758cf6d
    pass