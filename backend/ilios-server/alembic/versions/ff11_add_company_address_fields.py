"""Add structured address fields to companies table

Revision ID: ff11_company_address_fields
Revises: ff10_add_finance_data
Create Date: 2026-02-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ff11_company_address_fields"
down_revision: Union[str, None] = "ff10_add_finance_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    state_enum = sa.Enum(
        'AK','AL','AR','AZ','CA','CO','CT','DC','DE','FL','GA','HI','IA','ID','IL','IN',
        'KS','KY','LA','MA','MD','ME','MI','MN','MO','MS','MT','NC','ND','NE','NH','NJ',
        'NM','NV','NY','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VA','VT','WA',
        'WI','WV','WY',
        name='state',
        create_type=False
    )
    op.add_column('companies', sa.Column('city', sa.VARCHAR(), nullable=True))
    op.add_column('companies', sa.Column('state', state_enum, nullable=True))
    op.add_column('companies', sa.Column('county', sa.VARCHAR(), nullable=True))
    op.add_column('companies', sa.Column('zip_code', sa.VARCHAR(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'zip_code')
    op.drop_column('companies', 'county')
    op.drop_column('companies', 'state')
    op.drop_column('companies', 'city')
