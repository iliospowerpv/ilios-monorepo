"""Read-only usage observability for the AI Assistant (Slice 3, admin-only).

Aggregates ONLY over the two isolated assistant tables (``assistant_conversations`` /
``assistant_conversation_messages``). It touches NO operational/business data and performs NO
writes — every query is a SELECT. Simple counts run in SQL; the "top tools" tally reads a bounded,
recent slice of the ``used_tools`` JSONB and aggregates it in Python (the JSONB shape is a small
list of ``{name, ok, error}`` records).
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assistant import (
    AssistantConversation,
    AssistantConversationMessage,
    AssistantMessageFeedback,
    AssistantMessageRole,
)
from app.schema.assistant import AssistantToolUsageStat, AssistantUsageResponse

# Bound how many recent assistant messages we scan for tool usage so the tally can never fan out.
_TOOL_SCAN_CAP = 5000
# Cap how many distinct tools we report.
_TOP_TOOLS_CAP = 20


def build_usage_summary(db_session: Session) -> AssistantUsageResponse:
    """Compute the read-only assistant usage aggregate. Admin-gated by the caller (router)."""
    conv_q = db_session.query(AssistantConversation)
    conversations_total = conv_q.count()
    conversations_archived = conv_q.filter(
        AssistantConversation.is_archived.is_(True)
    ).count()
    conversations_active = conversations_total - conversations_archived
    distinct_users = (
        db_session.query(func.count(func.distinct(AssistantConversation.user_id))).scalar()
        or 0
    )

    msg_q = db_session.query(AssistantConversationMessage)
    messages_total = msg_q.count()
    user_messages = msg_q.filter(
        AssistantConversationMessage.role == AssistantMessageRole.user
    ).count()
    assistant_messages = messages_total - user_messages

    feedback_up = msg_q.filter(
        AssistantConversationMessage.feedback == AssistantMessageFeedback.up
    ).count()
    feedback_down = msg_q.filter(
        AssistantConversationMessage.feedback == AssistantMessageFeedback.down
    ).count()
    feedback_none = assistant_messages - feedback_up - feedback_down

    top_tools = _top_tools(db_session)

    return AssistantUsageResponse(
        conversations_total=conversations_total,
        conversations_active=conversations_active,
        conversations_archived=conversations_archived,
        messages_total=messages_total,
        user_messages=user_messages,
        assistant_messages=assistant_messages,
        distinct_users=int(distinct_users),
        feedback_up=feedback_up,
        feedback_down=feedback_down,
        feedback_none=max(0, feedback_none),
        top_tools=top_tools,
    )


def _top_tools(db_session: Session) -> list[AssistantToolUsageStat]:
    """Tally tool usage over a bounded, recent slice of assistant messages' ``used_tools`` JSONB."""
    rows = (
        db_session.query(AssistantConversationMessage.used_tools)
        .filter(
            AssistantConversationMessage.role == AssistantMessageRole.assistant,
            AssistantConversationMessage.used_tools.isnot(None),
        )
        .order_by(AssistantConversationMessage.id.desc())
        .limit(_TOOL_SCAN_CAP)
        .all()
    )
    counter: Counter[str] = Counter()
    for (used_tools,) in rows:
        if not isinstance(used_tools, list):
            continue
        for entry in used_tools:
            if isinstance(entry, dict):
                name = entry.get("name")
                if isinstance(name, str) and name:
                    counter[name] += 1
    return [
        AssistantToolUsageStat(name=name, count=count)
        for name, count in counter.most_common(_TOP_TOOLS_CAP)
    ]
