"""fix subscriber manager role name

Revision ID: 0bffd46a2191
Revises: 0063dad71dfb
Create Date: 2024-11-06 13:51:43.320227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bffd46a2191'
down_revision: Union[str, None] = '0063dad71dfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix role naming"""
    conn = op.get_bind()
    conn.execute(sa.text("""UPDATE roles SET name = 'Subscriber Manager'
    FROM company_type_role_mapping
    WHERE company_type_role_mapping.role_id = roles.id
    AND company_type_role_mapping.company_type = 'subscriber_manager';
    """))


def downgrade() -> None:
    """No backward migration is needed"""
    pass
