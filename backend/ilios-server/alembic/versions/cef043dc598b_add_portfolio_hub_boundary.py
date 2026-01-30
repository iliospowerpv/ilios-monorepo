"""Add portfolio hub boundary columns

Revision ID: cef043dc598b
Revises: 10e7daa5b8b9
Create Date: 2026-01-30

This migration introduces portfolio hub boundaries:
1. Adds portfolio_hub_id to companies table (self-referencing FK)
2. Adds portfolio_hub_company_id to user_portfolio_access table
3. Backfills existing user_portfolio_access rows safely

Semantics:
- companies.portfolio_hub_id = NULL means company is its own hub
- user_portfolio_access.portfolio_hub_company_id defines which hub the user has access to
"""
from alembic import op
import sqlalchemy as sa


revision = 'cef043dc598b'
down_revision = '10e7daa5b8b9'
branch_labels = None
depends_on = None


def upgrade():
    # Part A: Add portfolio_hub_id to companies
    op.add_column(
        'companies',
        sa.Column('portfolio_hub_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_companies_portfolio_hub_id',
        'companies', 'companies',
        ['portfolio_hub_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(
        'ix_companies_portfolio_hub_id',
        'companies',
        ['portfolio_hub_id']
    )
    
    # Part B: Add portfolio_hub_company_id to user_portfolio_access
    # First add as nullable
    op.add_column(
        'user_portfolio_access',
        sa.Column('portfolio_hub_company_id', sa.Integer(), nullable=True)
    )
    
    # Backfill strategy: For existing rows, we need to assign a hub.
    # Since we don't have a clear hub concept yet, we'll:
    # 1. Look up each user's parent_company_id as their default hub
    # 2. If no parent_company, set status to 'invited' (requires admin assignment)
    #
    # This query backfills using the user's parent_company_id as the hub
    op.execute("""
        UPDATE user_portfolio_access upa
        SET portfolio_hub_company_id = u.parent_company_id
        FROM users u
        WHERE upa.user_id = u.id
        AND u.parent_company_id IS NOT NULL
    """)
    
    # For users without a parent_company, set status to invited 
    # so they require explicit hub assignment
    op.execute("""
        UPDATE user_portfolio_access upa
        SET status = 'invited'
        FROM users u
        WHERE upa.user_id = u.id
        AND u.parent_company_id IS NULL
        AND upa.portfolio_hub_company_id IS NULL
        AND upa.status = 'active'
    """)
    
    # Create FK constraint
    op.create_foreign_key(
        'fk_user_portfolio_access_hub',
        'user_portfolio_access', 'companies',
        ['portfolio_hub_company_id'], ['id'],
        ondelete='CASCADE'
    )
    
    # Create index for hub lookups
    op.create_index(
        'ix_user_portfolio_access_hub_id',
        'user_portfolio_access',
        ['portfolio_hub_company_id']
    )
    
    # Drop old unique constraint and create new one
    op.drop_constraint('uq_user_portfolio_access', 'user_portfolio_access', type_='unique')
    op.create_unique_constraint(
        'uq_user_portfolio_access_per_hub',
        'user_portfolio_access',
        ['user_id', 'portfolio_hub_company_id']
    )


def downgrade():
    # Reverse Part B
    op.drop_constraint('uq_user_portfolio_access_per_hub', 'user_portfolio_access', type_='unique')
    op.create_unique_constraint(
        'uq_user_portfolio_access',
        'user_portfolio_access',
        ['user_id']
    )
    op.drop_index('ix_user_portfolio_access_hub_id', table_name='user_portfolio_access')
    op.drop_constraint('fk_user_portfolio_access_hub', 'user_portfolio_access', type_='foreignkey')
    op.drop_column('user_portfolio_access', 'portfolio_hub_company_id')
    
    # Reverse Part A
    op.drop_index('ix_companies_portfolio_hub_id', table_name='companies')
    op.drop_constraint('fk_companies_portfolio_hub_id', 'companies', type_='foreignkey')
    op.drop_column('companies', 'portfolio_hub_id')
