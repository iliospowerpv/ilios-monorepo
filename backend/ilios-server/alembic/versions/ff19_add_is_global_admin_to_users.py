"""Add is_global_admin column to users.

Revision ID: ff19_add_is_global_admin_to_users
Revises: ff18_telemetry_v2_introduce
Create Date: 2026-05-08

Phase 1 of the Global Admin feature. Adds a boolean column on users that,
when true, grants the user platform-wide bypass of per-company /
per-portfolio access checks. This is intended for testing, validation,
and support staff. It is distinct from `is_system_user`, which is
reserved for the internal automation account.

Safeguards (enforced in the application layer, not the schema):
  - Cap of 3 active global admins (configurable via MAX_GLOBAL_ADMINS).
  - Cannot self-grant or self-revoke.
  - Cannot modify the system user.
  - Cannot revoke the last remaining global admin.
  - Shorter session lifetime for global admin sessions.
  - All grants/revokes are written to audit_logs.

This migration is purely additive. Default = False, NOT NULL. No existing
rows are elevated. Initial seeding is performed out of band by an
operator running `python scripts/grant_global_admin.py <email>`.
"""
import sqlalchemy as sa
from alembic import op

revision = "ff19_add_is_global_admin_to_users"
down_revision = "ff18_telemetry_v2_introduce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_global_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_users_is_global_admin",
        "users",
        ["is_global_admin"],
        unique=False,
        postgresql_where=sa.text("is_global_admin = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_users_is_global_admin", table_name="users")
    op.drop_column("users", "is_global_admin")
