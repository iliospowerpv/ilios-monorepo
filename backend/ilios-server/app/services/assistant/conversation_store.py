"""Owner-scoped persistence for AI Assistant conversations.

This is the ONLY module in the assistant package that writes, and it writes EXCLUSIVELY to the two
isolated ``assistant_conversations`` tables — never to operational/business truth and never to the
legacy chatbot tables. Every read/write is scoped to ``current_user.id`` so one user can never see
or mutate another's threads.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.assistant import (
    AssistantConversation,
    AssistantConversationMessage,
    AssistantMessageFeedback,
    AssistantMessageRole,
)
from app.models.helpers import utcnow

_TITLE_MAX = 80
_LIST_CAP = 100


def _derive_title(first_message: str) -> str:
    text = (first_message or "").strip().replace("\n", " ")
    if not text:
        return "New conversation"
    return text[: _TITLE_MAX - 1] + "…" if len(text) > _TITLE_MAX else text


def list_conversations(
    db_session: Session, current_user, *, limit: int = 50
) -> list[AssistantConversation]:
    cap = max(1, min(int(limit or 50), _LIST_CAP))
    return (
        db_session.query(AssistantConversation)
        .filter(
            AssistantConversation.user_id == current_user.id,
            AssistantConversation.is_archived.is_(False),
        )
        .order_by(
            AssistantConversation.updated_at.desc(), AssistantConversation.id.desc()
        )
        .limit(cap)
        .all()
    )


def get_conversation(
    db_session: Session, current_user, conversation_id: int
) -> Optional[AssistantConversation]:
    return (
        db_session.query(AssistantConversation)
        .filter(
            AssistantConversation.id == conversation_id,
            AssistantConversation.user_id == current_user.id,
            AssistantConversation.is_archived.is_(False),
        )
        .one_or_none()
    )


def create_conversation(
    db_session: Session,
    current_user,
    *,
    company_id: Optional[int] = None,
    first_message: str = "",
) -> AssistantConversation:
    conv = AssistantConversation(
        user_id=current_user.id,
        company_id=company_id,
        title=_derive_title(first_message),
    )
    db_session.add(conv)
    db_session.flush()
    return conv


def append_turn(
    db_session: Session,
    conversation: AssistantConversation,
    *,
    user_message: str,
    reply: str,
    used_tools: list[dict],
    action_cards: list[dict],
    sources: Optional[list[dict]] = None,
    model: Optional[str],
) -> AssistantConversationMessage:
    """Persist the user turn + the assistant reply (with its transparency record) and commit.

    Returns the persisted ASSISTANT message so the caller can echo its id back to the client (for
    attaching feedback to the just-sent reply).
    """
    db_session.add(
        AssistantConversationMessage(
            conversation_id=conversation.id,
            role=AssistantMessageRole.user,
            content=user_message,
        )
    )
    assistant_message = AssistantConversationMessage(
        conversation_id=conversation.id,
        role=AssistantMessageRole.assistant,
        content=reply,
        used_tools=used_tools or None,
        action_cards=action_cards or None,
        sources=sources or None,
        model=model,
    )
    db_session.add(assistant_message)
    # Appending child messages does not otherwise touch the parent row, so the model's
    # ``onupdate`` never fires; bump ``updated_at`` explicitly so the history list orders and
    # timestamps by last activity rather than by thread creation.
    conversation.updated_at = utcnow()
    db_session.commit()
    db_session.refresh(conversation)
    db_session.refresh(assistant_message)
    return assistant_message


def set_feedback(
    db_session: Session,
    current_user,
    *,
    conversation_id: int,
    message_id: int,
    rating: Optional[str],
    note: Optional[str],
) -> Optional[AssistantConversationMessage]:
    """Owner-scoped thumbs feedback on an ASSISTANT message. Returns the message, or None when the
    conversation/message isn't the caller's, doesn't exist, or isn't an assistant turn.

    Writes ONLY to the isolated assistant message row — never a governed/business action. ``rating``
    of None clears the rating (and any note); a non-None rating optionally stores a note too.
    """
    conv = get_conversation(db_session, current_user, conversation_id)
    if conv is None:
        return None
    message = (
        db_session.query(AssistantConversationMessage)
        .filter(
            AssistantConversationMessage.id == message_id,
            AssistantConversationMessage.conversation_id == conv.id,
            AssistantConversationMessage.role == AssistantMessageRole.assistant,
        )
        .one_or_none()
    )
    if message is None:
        return None
    if rating is None:
        message.feedback = None
        message.feedback_note = None
    else:
        message.feedback = AssistantMessageFeedback(rating)
        message.feedback_note = (note or None)
    db_session.commit()
    db_session.refresh(message)
    return message


def archive_conversation(
    db_session: Session, current_user, conversation_id: int
) -> bool:
    """Soft-delete (owner-scoped). Returns False when the thread isn't the caller's / doesn't exist."""
    conv = get_conversation(db_session, current_user, conversation_id)
    if conv is None:
        return False
    conv.is_archived = True
    db_session.commit()
    return True
