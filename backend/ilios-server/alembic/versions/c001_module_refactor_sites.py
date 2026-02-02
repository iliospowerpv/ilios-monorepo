"""Add project name and signed agreement fields to sites

Revision ID: c001a1b2c3d4
Revises: b94da896de34
Create Date: 2026-02-02

Adds:
- constructed_name: system-generated project name
- name_override: admin-editable override
- signed_agreement_status: missing/uploaded/waived
- signed_agreement tracking fields
"""

from alembic import op
import sqlalchemy as sa


revision = "c001a1b2c3d4"
down_revision = "b94da896de34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sites",
        sa.Column("constructed_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column("name_override", sa.String(255), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column("name_override_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column("name_override_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column("signed_agreement_status", sa.String(20), nullable=True, server_default="missing"),
    )
    op.add_column(
        "sites",
        sa.Column("signed_agreement_document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column("waived_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column("waived_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column("waiver_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sites", "waiver_reason")
    op.drop_column("sites", "waived_at")
    op.drop_column("sites", "waived_by_id")
    op.drop_column("sites", "signed_agreement_document_id")
    op.drop_column("sites", "signed_agreement_status")
    op.drop_column("sites", "name_override_at")
    op.drop_column("sites", "name_override_by_id")
    op.drop_column("sites", "name_override")
    op.drop_column("sites", "constructed_name")
