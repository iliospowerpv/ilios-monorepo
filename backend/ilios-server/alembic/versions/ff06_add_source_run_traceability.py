"""Add source_run_id to project_facts for complete traceability

Revision ID: ff06
Revises: ff05
Create Date: 2026-02-04
"""
from alembic import op
import sqlalchemy as sa


revision = 'ff06_source_run_traceability'
down_revision = 'ff05_parsing_job_bindings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('project_facts', sa.Column('source_run_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_project_facts_source_run_id',
        'project_facts',
        'ai_parsing_results',
        ['source_run_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_project_facts_source_run', 'project_facts', ['source_run_id'])


def downgrade() -> None:
    op.drop_index('ix_project_facts_source_run', table_name='project_facts')
    op.drop_constraint('fk_project_facts_source_run_id', 'project_facts', type_='foreignkey')
    op.drop_column('project_facts', 'source_run_id')
