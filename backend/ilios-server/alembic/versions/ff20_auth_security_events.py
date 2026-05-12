"""Add auth_security_events table.

Revision ID: ff20_auth_security_events
Revises: ff19_add_is_global_admin_to_users
Create Date: 2026-05-12

Phase 0B auth abuse protection. Backs:
  * per-IP login rate limiting (DB-counted, survives process restart)
  * per-account failed-login lockout / cooldown
  * password reset throttling (per-IP and per-email)
  * operator visibility into recent auth security events

The table is append-only from the application layer except for an
explicit "clear failed logins on success" cleanup.
"""
import sqlalchemy as sa
from alembic import op

revision = "ff20_auth_security_events"
down_revision = "ff19_add_is_global_admin_to_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_security_events",
        sa.Column("id", sa.Integer(), sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("timezone('utc', now())"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("normalized_identifier_hash", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_auth_security_events_created_at",
        "auth_security_events",
        [sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_auth_security_events_identifier_created",
        "auth_security_events",
        ["normalized_identifier_hash", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_auth_security_events_ip_created",
        "auth_security_events",
        ["ip_address", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_auth_security_events_event_outcome",
        "auth_security_events",
        ["event_type", "outcome"],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_security_events_event_outcome", table_name="auth_security_events")
    op.drop_index("ix_auth_security_events_ip_created", table_name="auth_security_events")
    op.drop_index("ix_auth_security_events_identifier_created", table_name="auth_security_events")
    op.drop_index("ix_auth_security_events_created_at", table_name="auth_security_events")
    op.drop_table("auth_security_events")
