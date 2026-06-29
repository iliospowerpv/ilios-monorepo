"""AI Assistant feedback + source disclosures — additive columns on the isolated message table.

Revision ID: ff42_assistant_feedback_sources
Revises: ff41_assistant_conversations
Create Date: 2026-06-29

Background
----------
Slice 3 additions, all ADDITIVE and confined to the already-isolated
``assistant_conversation_messages`` table (still nothing shared with the legacy Due-Diligence
chatbot, the tool layer still stays zero-write — only ``conversation_store`` writes here):

* ``sources`` (JSONB, nullable) — the labels-only transparency record of which knowledge sources
  (curated FAQ entries / read-only data tools) backed an assistant turn. Stored at write time so
  the persisted transcript can disclose sources later without reconstructing them.
* ``feedback`` (enum ``assistant_message_feedback_enum`` = up/down, nullable) — optional
  owner-supplied thumbs up/down on an assistant turn.
* ``feedback_note`` (Text, nullable) — optional free-text note accompanying the rating.

Hard invariants: additive only — no existing column is altered or dropped; no other table touched.

Rollback
--------
``downgrade()`` drops the three columns then the feedback enum type. Nothing pre-existing is touched.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff42_assistant_feedback_sources"
down_revision = "ff41_assistant_conversations"
branch_labels = None
depends_on = None


ASSISTANT_MESSAGE_FEEDBACK_ENUM_NAME = "assistant_message_feedback_enum"
ASSISTANT_MESSAGE_FEEDBACK = ("up", "down")


def _feedback_enum():
    return postgresql.ENUM(
        *ASSISTANT_MESSAGE_FEEDBACK,
        name=ASSISTANT_MESSAGE_FEEDBACK_ENUM_NAME,
        create_type=False,
    )


def upgrade() -> None:
    bind = op.get_bind()

    _feedback_enum().create(bind, checkfirst=True)

    op.add_column(
        "assistant_conversation_messages",
        sa.Column("sources", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "assistant_conversation_messages",
        sa.Column("feedback", _feedback_enum(), nullable=True),
    )
    op.add_column(
        "assistant_conversation_messages",
        sa.Column("feedback_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_column("assistant_conversation_messages", "feedback_note")
    op.drop_column("assistant_conversation_messages", "feedback")
    op.drop_column("assistant_conversation_messages", "sources")

    _feedback_enum().drop(bind, checkfirst=True)
