"""limit das connection name len

Revision ID: 2b34cb4131de
Revises: 2d0b27f6afb8
Create Date: 2024-11-07 12:21:54.021215

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b34cb4131de'
down_revision: Union[str, None] = '2d0b27f6afb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix das connection name len:
    if it's less than 2 - add dot symbol,
    if it's more than 100 - truncate to first 100"""
    conn = op.get_bind()
    update_statement = sa.text("""UPDATE das_connections
    SET name = 
        CASE 
            WHEN LENGTH(name) < 2 THEN RPAD(name, 2, '.')
            WHEN LENGTH(name) > 100 THEN LEFT(name, 100)
            ELSE name
        END
    WHERE LENGTH(name) < 2 OR LENGTH(name) > 100;
    """)
    conn.execute(update_statement)


def downgrade() -> None:
    """No backward migration is needed"""
    pass
