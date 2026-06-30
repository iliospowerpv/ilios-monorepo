"""AI Assistant persistence (ADDITIVE, isolated).

Two distinct, isolated write surfaces live here — both share NOTHING with the legacy Due-Diligence
chatbot (``chatbot_conversations``) and neither is ever a source of operational/business truth:

1. Conversation persistence (``assistant_conversations`` / ``assistant_conversation_messages``).
   The ONLY place the read-only assistant *reasoning path* writes — it stores the chat transcript so
   a user can revisit prior conversations. The assistant's TOOL layer remains zero-write; the LLM /
   tool path never writes anything else.

2. UI-interaction analytics (``assistant_ui_events``). A privacy-bounded, first-party product
   telemetry sink written EXCLUSIVELY by an explicit, authenticated ingest endpoint when the user
   interacts with the assistant UI (opens it, clicks a card, dismisses a hint, …). It is NOT part of
   the assistant/tool/LLM path and is never callable as a tool. It stores ONLY a bounded event name,
   a coarse route bucket, a small allowlisted detail token, and an in-companion flag — never prompt
   or reply content, and never any operational/business value or entity id.
"""
import enum

from sqlalchemy import (
    VARCHAR,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from app.db.base_class import Base
from app.models.helpers import utcnow

ASSISTANT_MESSAGE_ROLE_ENUM_NAME = "assistant_message_role_enum"
ASSISTANT_MESSAGE_FEEDBACK_ENUM_NAME = "assistant_message_feedback_enum"
ASSISTANT_UI_EVENT_ENUM_NAME = "assistant_ui_event_enum"


class AssistantMessageRole(enum.Enum):
    """Persisted turn author. Only final user/assistant turns are stored (never tool frames)."""

    user = "user"
    assistant = "assistant"


class AssistantMessageFeedback(enum.Enum):
    """Optional owner-supplied thumbs rating on an assistant turn (Slice 3)."""

    up = "up"
    down = "down"


class AssistantUiEventName(enum.Enum):
    """Bounded allowlist of first-party assistant UI-interaction events (Task #89).

    This is a CLOSED set — the ingest endpoint rejects any name outside it. Each value names a
    discrete, non-identifying UI interaction. NONE of them carry message/reply content or any
    operational/business value; they exist purely to measure assistant adoption (opens, dismissals,
    discoverability clicks, …). Feedback ratings and raw user-message counts are intentionally
    ABSENT because they are already derivable from the conversation message store.
    """

    assistant_opened = "assistant_opened"
    assistant_dismissed = "assistant_dismissed"
    prompt_submitted = "prompt_submitted"
    suggested_prompt_clicked = "suggested_prompt_clicked"
    action_card_clicked = "action_card_clicked"
    sources_disclosure_opened = "sources_disclosure_opened"
    first_run_shown = "first_run_shown"
    first_run_dismissed = "first_run_dismissed"
    first_run_opened = "first_run_opened"
    proactive_hint_shown = "proactive_hint_shown"
    proactive_hint_dismissed = "proactive_hint_dismissed"
    proactive_hint_opened = "proactive_hint_opened"
    discoverability_entry_clicked = "discoverability_entry_clicked"


class AssistantConversation(Base):
    """One chat thread, owned by exactly one user. Soft-deleted via ``is_archived``."""

    __tablename__ = "assistant_conversations"

    __table_args__ = (
        Index("ix_assistant_conversations_user_id", "user_id"),
        Index("ix_assistant_conversations_user_archived", "user_id", "is_archived"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    # Owner. CASCADE so a deleted user takes their private chat history with them.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # Optional advisory scope captured from the UI when the thread was opened.
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    title = Column(VARCHAR, nullable=True)
    is_archived = Column(
        Boolean, nullable=False, default=False, server_default=expression.false()
    )

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    messages = relationship(
        "AssistantConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantConversationMessage.id",
    )


class AssistantConversationMessage(Base):
    """A single persisted turn. Assistant turns also carry the transparency record of which
    read-only tools ran and any propose-only action cards offered (both JSONB, advisory only)."""

    __tablename__ = "assistant_conversation_messages"

    __table_args__ = (
        Index(
            "ix_assistant_conversation_messages_conversation_id", "conversation_id"
        ),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    conversation_id = Column(
        Integer,
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(
        Enum(AssistantMessageRole, name=ASSISTANT_MESSAGE_ROLE_ENUM_NAME),
        nullable=False,
    )
    content = Column(Text, nullable=False)
    used_tools = Column(JSONB, nullable=True)
    action_cards = Column(JSONB, nullable=True)
    # Labels-only transparency record of which knowledge sources backed this turn (Slice 3).
    sources = Column(JSONB, nullable=True)
    model = Column(VARCHAR, nullable=True)
    # Optional owner-supplied thumbs rating + note on an assistant turn (Slice 3).
    feedback = Column(
        Enum(AssistantMessageFeedback, name=ASSISTANT_MESSAGE_FEEDBACK_ENUM_NAME),
        nullable=True,
    )
    feedback_note = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=utcnow())

    conversation = relationship("AssistantConversation", back_populates="messages")


class AssistantUiEvent(Base):
    """One privacy-bounded, first-party assistant UI-interaction event (Task #89).

    Written EXCLUSIVELY by the authenticated ``POST /api/assistant/events`` ingest endpoint — never
    by the assistant/tool/LLM path and never exposed as a tool. Every field is bounded and
    non-identifying so the row can never become a source of operational truth or a hidden user
    profile:

    * ``user_id`` — auth-derived (never client-supplied); used ONLY for cascade-on-delete and
      aggregate distinct counts. No API ever returns per-user analytics.
    * ``event`` — a value from the closed :class:`AssistantUiEventName` allowlist.
    * ``route_bucket`` — a coarse, server-normalized route token (e.g. ``project_hub``) with all
      entity ids stripped; never a raw path.
    * ``detail`` — a small, per-event allowlisted qualifier token (e.g. the clicked card's kind);
      anything not on that event's allowlist is dropped to NULL.
    * ``in_companion`` — whether the interaction happened inside a guided workflow wizard.
    """

    __tablename__ = "assistant_ui_events"

    __table_args__ = (
        Index("ix_assistant_ui_events_event", "event"),
        Index("ix_assistant_ui_events_user_id", "user_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    # Auth-derived owner. CASCADE so a deleted user takes their telemetry with them.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event = Column(
        Enum(AssistantUiEventName, name=ASSISTANT_UI_EVENT_ENUM_NAME),
        nullable=False,
    )
    # Coarse, server-normalized route token (entity ids stripped). Never a raw path.
    route_bucket = Column(VARCHAR, nullable=True)
    # Small, per-event allowlisted qualifier (e.g. a card kind). NULL when not applicable.
    detail = Column(VARCHAR, nullable=True)
    in_companion = Column(
        Boolean, nullable=False, default=False, server_default=expression.false()
    )

    created_at = Column(DateTime, server_default=utcnow())
