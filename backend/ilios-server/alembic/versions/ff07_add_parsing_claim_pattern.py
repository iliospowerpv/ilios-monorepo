"""Add claim pattern columns for parsing idempotency and concurrency

Revision ID: ff07
Revises: ff06
Create Date: 2026-02-04
"""
from alembic import op
import sqlalchemy as sa


revision = 'ff07_parsing_claim_pattern'
down_revision = 'ff06_source_run_traceability'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE fileparsingstatuses ADD VALUE IF NOT EXISTS 'queued'")
    
    op.add_column('ai_parsing_results', sa.Column('worker_id', sa.String(100), nullable=True))
    op.add_column('ai_parsing_results', sa.Column('correlation_id', sa.String(50), nullable=True))
    op.add_column('ai_parsing_results', sa.Column('claimed_at', sa.DateTime(), nullable=True))
    
    op.create_index('ix_ai_parsing_results_file_status', 'ai_parsing_results', ['file_id', 'status'])
    op.create_index('ix_ai_parsing_results_correlation', 'ai_parsing_results', ['correlation_id'])
    
    op.execute("""
        CREATE UNIQUE INDEX ix_ai_parsing_results_active_unique 
        ON ai_parsing_results (
            file_id, 
            COALESCE(document_type_id, -1), 
            COALESCE(schema_version_id, -1), 
            COALESCE(prompt_template_id, -1)
        )
        WHERE status IN ('queued', 'processing')
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ai_parsing_results_active_unique")
    op.drop_index('ix_ai_parsing_results_correlation', table_name='ai_parsing_results')
    op.drop_index('ix_ai_parsing_results_file_status', table_name='ai_parsing_results')
    op.drop_column('ai_parsing_results', 'claimed_at')
    op.drop_column('ai_parsing_results', 'correlation_id')
    op.drop_column('ai_parsing_results', 'worker_id')
