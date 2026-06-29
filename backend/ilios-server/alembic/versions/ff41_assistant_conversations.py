"""AI Assistant conversation persistence — additive, isolated tables.

Revision ID: ff41_assistant_conversations
Revises: ff40_workflow_orchestration_lineage
Create Date: 2026-06-29

Background
----------
Adds the two tables that back AI Assistant conversation persistence (Slice 2). They store ONLY the
chat transcript so a user can revisit prior conversations — never operational/business truth — and
they share NOTHING with the legacy Due-Diligence chatbot. The assistant's tool layer stays
zero-write; persistence lives exclusively here.

* ``assistant_conversations`` — one chat thread owned by exactly one user (``user_id`` CASCADE),
  with an optional advisory ``company_id`` scope (SET NULL) and a soft-delete ``is_archived`` flag.
* ``assistant_conversation_messages`` — one persisted turn (user/assistant), the assistant turn
  also carrying the read-only ``used_tools`` transparency record and propose-only ``action_cards``
  (both JSONB, advisory only). ``conversation_id`` CASCADE.

Hard invariants: additive only — NO existing table is modified; foreign keys reference
``users``/``companies`` with safe ON DELETE.

Rollback
--------
``downgrade()`` drops the two tables (and their indexes) then the enum type. No pre-existing
object is touched.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff41_assistant_conversations"
down_revision = "ff40_workflow_orchestration_lineage"
branch_labels = None
depends_on = None


# Enum type name (kept in lockstep with app/models/assistant.py).
ASSISTANT_MESSAGE_ROLE_ENUM_NAME = "assistant_message_role_enum"
ASSISTANT_MESSAGE_ROLES = ("user", "assistant")


def _enum(name, values):
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    _enum(ASSISTANT_MESSAGE_ROLE_ENUM_NAME, ASSISTANT_MESSAGE_ROLES).create(
        bind, checkfirst=True
    )

    # ------------------------------------------------------------------
    # 1. assistant_conversations
    # ------------------------------------------------------------------
    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            sa.Integer,
            sa.ForeignKey("companies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column(
            "is_archived",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_assistant_conversations_user_id", "assistant_conversations", ["user_id"]
    )
    op.create_index(
        "ix_assistant_conversations_user_archived",
        "assistant_conversations",
        ["user_id", "is_archived"],
    )

    # ------------------------------------------------------------------
    # 2. assistant_conversation_messages
    # ------------------------------------------------------------------
    op.create_table(
        "assistant_conversation_messages",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer,
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            _enum(ASSISTANT_MESSAGE_ROLE_ENUM_NAME, ASSISTANT_MESSAGE_ROLES),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("used_tools", postgresql.JSONB, nullable=True),
        sa.Column("action_cards", postgresql.JSONB, nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_assistant_conversation_messages_conversation_id",
        "assistant_conversation_messages",
        ["conversation_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        "ix_assistant_conversation_messages_conversation_id",
        table_name="assistant_conversation_messages",
    )
    op.drop_table("assistant_conversation_messages")

    op.drop_index(
        "ix_assistant_conversations_user_archived",
        table_name="assistant_conversations",
    )
    op.drop_index(
        "ix_assistant_conversations_user_id", table_name="assistant_conversations"
    )
    op.drop_table("assistant_conversations")

    _enum(ASSISTANT_MESSAGE_ROLE_ENUM_NAME, ASSISTANT_MESSAGE_ROLES).drop(
        bind, checkfirst=True
    )
