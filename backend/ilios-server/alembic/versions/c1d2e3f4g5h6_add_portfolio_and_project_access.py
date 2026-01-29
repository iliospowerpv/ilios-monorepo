"""Add portfolio access and enhance project access

Revision ID: c1d2e3f4g5h6
Revises: b1c2d3e4f5g6
Create Date: 2026-01-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c1d2e3f4g5h6'
down_revision: Union[str, None] = 'b1c2d3e4f5g6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_portfolio_access',
        sa.Column('id', sa.Integer(), sa.Identity(always=False, start=1, increment=1), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', postgresql.ENUM('company_admin', 'contributor', 'read_only', name='companyrole', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('active', 'invited', 'disabled', name='membershipstatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_portfolio_access_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_user_portfolio_access_created_by_user_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_portfolio_access')),
        sa.UniqueConstraint('user_id', name='uq_user_portfolio_access')
    )
    op.create_index('ix_user_portfolio_access_user_id', 'user_portfolio_access', ['user_id'], unique=False)
    
    op.add_column('user_projects', sa.Column('role', postgresql.ENUM('company_admin', 'contributor', 'read_only', name='companyrole', create_type=False), nullable=True))
    op.add_column('user_projects', sa.Column('status', postgresql.ENUM('active', 'invited', 'disabled', name='membershipstatus', create_type=False), nullable=True))
    op.add_column('user_projects', sa.Column('created_by_user_id', sa.Integer(), nullable=True))
    
    op.execute("UPDATE user_projects SET role = 'contributor' WHERE role IS NULL")
    op.execute("UPDATE user_projects SET status = 'active' WHERE status IS NULL")
    
    op.alter_column('user_projects', 'role', nullable=False)
    op.alter_column('user_projects', 'status', nullable=False)
    
    op.create_foreign_key(
        'fk_user_projects_created_by_user_id_users',
        'user_projects', 'users',
        ['created_by_user_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_index('ix_user_project_site_id', 'user_projects', ['site_id'], unique=False, if_not_exists=True)
    op.create_index('ix_user_project_user_id', 'user_projects', ['user_id'], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_index('ix_user_project_user_id', table_name='user_projects', if_exists=True)
    op.drop_index('ix_user_project_site_id', table_name='user_projects', if_exists=True)
    
    op.drop_constraint('fk_user_projects_created_by_user_id_users', 'user_projects', type_='foreignkey')
    op.drop_column('user_projects', 'created_by_user_id')
    op.drop_column('user_projects', 'status')
    op.drop_column('user_projects', 'role')
    
    op.drop_index('ix_user_portfolio_access_user_id', table_name='user_portfolio_access')
    op.drop_table('user_portfolio_access')
