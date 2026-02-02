"""Extend document_keys for extraction workflow

Revision ID: c002a1b2c3d4
Revises: c001a1b2c3d4
Create Date: 2026-02-02

Adds:
- source: ai_extraction or manual_entry
- status: proposed/accepted/overridden/rejected
- acceptance tracking fields
- override fields
- canonical_field mapping
"""

from alembic import op
import sqlalchemy as sa


revision = "c002a1b2c3d4"
down_revision = "c001a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_keys",
        sa.Column("source", sa.String(20), nullable=True, server_default="manual_entry"),
    )
    op.add_column(
        "document_keys",
        sa.Column("status", sa.String(20), nullable=True, server_default="accepted"),
    )
    op.add_column(
        "document_keys",
        sa.Column("accepted_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "document_keys",
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "document_keys",
        sa.Column("override_value", sa.String(), nullable=True),
    )
    op.add_column(
        "document_keys",
        sa.Column("overridden_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "document_keys",
        sa.Column("overridden_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "document_keys",
        sa.Column("canonical_field", sa.String(100), nullable=True),
    )
    
    op.create_index("idx_document_keys_status", "document_keys", ["status"])
    op.create_index("idx_document_keys_canonical_field", "document_keys", ["canonical_field"])


def downgrade() -> None:
    op.drop_index("idx_document_keys_canonical_field")
    op.drop_index("idx_document_keys_status")
    op.drop_column("document_keys", "canonical_field")
    op.drop_column("document_keys", "overridden_at")
    op.drop_column("document_keys", "overridden_by_id")
    op.drop_column("document_keys", "override_value")
    op.drop_column("document_keys", "accepted_at")
    op.drop_column("document_keys", "accepted_by_id")
    op.drop_column("document_keys", "status")
    op.drop_column("document_keys", "source")
