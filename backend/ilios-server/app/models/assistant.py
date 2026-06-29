"""AI Assistant conversation persistence (ADDITIVE, isolated).

These two tables are the ONLY place the read-only AI Assistant writes. They store the chat
transcript so a user can revisit prior conversations — nothing here is operational/business truth,
and they share NOTHING with the legacy Due-Diligence chatbot (``chatbot_conversations``). The
assistant's tool layer remains zero-write; persistence lives exclusively in these isolated tables.
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


class AssistantMessageRole(enum.Enum):
    """Persisted turn author. Only final user/assistant turns are stored (never tool frames)."""

    user = "user"
    assistant = "assistant"


class AssistantMessageFeedback(enum.Enum):
    """Optional owner-supplied thumbs rating on an assistant turn (Slice 3)."""

    up = "up"
    down = "down"


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
