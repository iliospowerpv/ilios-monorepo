"""AI Assistant UI-interaction analytics — additive, isolated table (Task #89).

Revision ID: ff43_assistant_ui_events
Revises: ff42_assistant_feedback_sources
Create Date: 2026-06-30

Background
----------
Adds the isolated ``assistant_ui_events`` table backing privacy-bounded, first-party assistant
product analytics. It is written EXCLUSIVELY by the authenticated ``POST /api/assistant/events``
ingest endpoint when a user interacts with the assistant UI — NEVER by the assistant/tool/LLM path,
and never exposed as a tool. It shares NOTHING with the legacy Due-Diligence chatbot and is never a
source of operational/business truth.

Every column is bounded and non-identifying:

* ``user_id`` (FK ``users`` CASCADE, NOT NULL) — auth-derived; used only for cascade-on-delete and
  aggregate distinct counts.
* ``event`` (enum ``assistant_ui_event_enum``) — a value from the closed UI-event allowlist.
* ``route_bucket`` (VARCHAR, nullable) — a coarse, server-normalized route token (entity ids
  stripped); never a raw path.
* ``detail`` (VARCHAR, nullable) — a small, per-event allowlisted qualifier token.
* ``in_companion`` (Boolean) — whether the interaction happened inside a guided workflow wizard.

Hard invariants: additive only — NO existing table is modified; the FK references ``users`` with a
safe ON DELETE CASCADE.

Rollback
--------
``downgrade()`` drops the table (and its indexes) then the enum type. No pre-existing object is
touched.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ff43_assistant_ui_events"
down_revision = "ff42_assistant_feedback_sources"
branch_labels = None
depends_on = None


# Enum type name (kept in lockstep with app/models/assistant.py:AssistantUiEventName).
ASSISTANT_UI_EVENT_ENUM_NAME = "assistant_ui_event_enum"
ASSISTANT_UI_EVENTS = (
    "assistant_opened",
    "assistant_dismissed",
    "prompt_submitted",
    "suggested_prompt_clicked",
    "action_card_clicked",
    "sources_disclosure_opened",
    "first_run_shown",
    "first_run_dismissed",
    "first_run_opened",
    "proactive_hint_shown",
    "proactive_hint_dismissed",
    "proactive_hint_opened",
    "discoverability_entry_clicked",
)


def _event_enum():
    return postgresql.ENUM(
        *ASSISTANT_UI_EVENTS,
        name=ASSISTANT_UI_EVENT_ENUM_NAME,
        create_type=False,
    )


def upgrade() -> None:
    bind = op.get_bind()

    _event_enum().create(bind, checkfirst=True)

    op.create_table(
        "assistant_ui_events",
        sa.Column("id", sa.Integer, sa.Identity(start=1, increment=1), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", _event_enum(), nullable=False),
        sa.Column("route_bucket", sa.String(), nullable=True),
        sa.Column("detail", sa.String(), nullable=True),
        sa.Column(
            "in_companion",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_assistant_ui_events_event", "assistant_ui_events", ["event"])
    op.create_index(
        "ix_assistant_ui_events_user_id", "assistant_ui_events", ["user_id"]
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_assistant_ui_events_user_id", table_name="assistant_ui_events")
    op.drop_index("ix_assistant_ui_events_event", table_name="assistant_ui_events")
    op.drop_table("assistant_ui_events")

    _event_enum().drop(bind, checkfirst=True)
