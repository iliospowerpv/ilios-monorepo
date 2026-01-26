"""Add user_company_access table

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f6
Create Date: 2026-01-26 20:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    companyrole_enum = postgresql.ENUM('company_admin', 'contributor', 'read_only', name='companyrole', create_type=False)
    companyrole_enum.create(op.get_bind(), checkfirst=True)
    
    membershipstatus_enum = postgresql.ENUM('active', 'invited', 'disabled', name='membershipstatus', create_type=False)
    membershipstatus_enum.create(op.get_bind(), checkfirst=True)
    
    op.create_table('user_company_access',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('role', postgresql.ENUM('company_admin', 'contributor', 'read_only', name='companyrole', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'invited', 'disabled', name='membershipstatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], name=op.f('fk_user_company_access_company_id_companies'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_company_access_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_user_company_access_created_by_user_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_company_access')),
        sa.UniqueConstraint('user_id', 'company_id', name='uq_user_company_access')
    )
    op.create_index('ix_user_company_access_company_id', 'user_company_access', ['company_id'], unique=False)
    op.create_index('ix_user_company_access_user_id', 'user_company_access', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_user_company_access_user_id', table_name='user_company_access')
    op.drop_index('ix_user_company_access_company_id', table_name='user_company_access')
    op.drop_table('user_company_access')
    
    postgresql.ENUM('company_admin', 'contributor', 'read_only', name='companyrole').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM('active', 'invited', 'disabled', name='membershipstatus').drop(op.get_bind(), checkfirst=True)
