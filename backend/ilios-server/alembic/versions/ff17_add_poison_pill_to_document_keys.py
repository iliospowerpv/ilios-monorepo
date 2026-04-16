"""Add is_poison_pill and poison_pill_notes to document_keys

Revision ID: ff17_add_poison_pill_to_document_keys
Revises: ff16_add_is_demo_to_companies
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa

revision = "ff17_add_poison_pill_to_document_keys"
down_revision = "ff16_add_is_demo_to_companies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_keys",
        sa.Column("is_poison_pill", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "document_keys",
        sa.Column("poison_pill_notes", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("document_keys", "poison_pill_notes")
    op.drop_column("document_keys", "is_poison_pill")
