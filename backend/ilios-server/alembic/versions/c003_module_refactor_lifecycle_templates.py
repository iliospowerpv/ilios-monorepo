"""Create lifecycle_task_templates table

Revision ID: c003a1b2c3d4
Revises: c002a1b2c3d4
Create Date: 2026-02-02

Creates lifecycle_task_templates for auto-creating tasks on lifecycle transitions.
"""

from alembic import op
import sqlalchemy as sa


revision = "c003a1b2c3d4"
down_revision = "c002a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lifecycle_task_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("to_state", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_offset_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("assignment_strategy", sa.String(50), nullable=True, server_default="company_admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    
    op.create_index("idx_lifecycle_task_templates_to_state", "lifecycle_task_templates", ["to_state"])
    
    op.execute("""
        INSERT INTO lifecycle_task_templates (to_state, title, description, due_offset_days, assignment_strategy)
        VALUES
        ('diligence', 'Complete diligence checklist review', 'Review and complete all Data Room checklist items', 14, 'company_admin'),
        ('diligence', 'Upload signed agreement', 'Upload MIPA or term sheet to Data Room', 7, 'company_admin'),
        ('implementation', 'Schedule construction kickoff', 'Coordinate with EPC contractor for project kickoff', 14, 'company_admin'),
        ('implementation', 'Finalize interconnection agreement', 'Ensure utility interconnection documents are complete', 30, 'contributor'),
        ('placed_in_service', 'Complete commissioning checklist', 'Verify all systems operational and documented', 7, 'company_admin'),
        ('placed_in_service', 'Submit PTO application', 'Submit permission to operate to utility', 3, 'contributor'),
        ('operations', 'Setup monitoring dashboards', 'Configure O&M dashboards and alert thresholds', 14, 'contributor'),
        ('operations', 'Complete handoff documentation', 'Finalize all project handoff documentation', 7, 'company_admin');
    """)


def downgrade() -> None:
    op.drop_index("idx_lifecycle_task_templates_to_state")
    op.drop_table("lifecycle_task_templates")
