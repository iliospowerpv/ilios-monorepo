"""AI Assistant router — read-only chat + isolated conversation persistence.

The whole surface is gated behind ``settings.native_assistant_enabled`` (404 when off) so it can roll
out independently of the legacy Due-Diligence chatbot, which it shares nothing with. ``POST /chat``
runs the read-only assistant AS the authenticated caller; conversation persistence (when requested)
writes ONLY to the isolated ``assistant_conversations`` tables. Every conversation read/write is
owner-scoped to the current user.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.schema.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConfigResponse,
    AssistantConversationDetailResponse,
    AssistantConversationListResponse,
    AssistantConversationSummary,
    AssistantPersistedMessage,
)
from app.schema.user import CurrentUserSchema
from app.services.assistant import conversation_store, llm_client
from app.services.assistant.assistant_service import run_assistant_chat
from app.services.assistant.tools import ALLOWED_TOOLS
from app.services.workflows.orchestration_context_service import PROHIBITED_ACTIONS
from app.settings import settings

assistant_router = APIRouter()


def _require_enabled() -> None:
    if not settings.native_assistant_enabled:
        # Hidden, not 403: when the flag is off the feature simply does not exist.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _parse_conversation_id(raw: str) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )


@assistant_router.get("/config", response_model=AssistantConfigResponse)
def assistant_config(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> AssistantConfigResponse:
    """Capability/probe payload. Reachable only when the flag is on, so a 200 means 'available'."""
    _require_enabled()
    return AssistantConfigResponse(
        enabled=True,
        model=llm_client.ASSISTANT_MODEL,
        available_tools=sorted(ALLOWED_TOOLS),
        prohibited_actions=list(PROHIBITED_ACTIONS),
    )


@assistant_router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(
    payload: AssistantChatRequest,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AssistantChatResponse:
    """Answer a single chat turn using the read-only tool catalog.

    Reasoning stays stateless (the client supplies prior turns in ``history``). When ``persist`` is
    set or a ``conversation_id`` is supplied, the turn is additionally recorded in the isolated
    assistant conversation store and the resolved conversation id is echoed back.
    """
    _require_enabled()

    # Fail-fast: validate ownership of a supplied conversation id BEFORE spending any LLM/tool work,
    # so an invalid or cross-user id 404s cheaply (owner-scoped — cross-user resolves to None → 404).
    conv = None
    if payload.conversation_id:
        conv = conversation_store.get_conversation(
            db_session, current_user, _parse_conversation_id(payload.conversation_id)
        )
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )

    response = run_assistant_chat(db_session, current_user, payload)

    if not (payload.persist or payload.conversation_id):
        return response

    if conv is None:
        company_id = payload.context.company_id if payload.context else None
        conv = conversation_store.create_conversation(
            db_session,
            current_user,
            company_id=company_id,
            first_message=payload.message,
        )

    conversation_store.append_turn(
        db_session,
        conv,
        user_message=payload.message,
        reply=response.reply,
        used_tools=[t.model_dump(mode="json") for t in response.used_tools],
        action_cards=[c.model_dump(mode="json") for c in response.action_cards],
        model=response.model,
    )
    response.conversation_id = str(conv.id)
    return response


@assistant_router.get("/conversations", response_model=AssistantConversationListResponse)
def list_conversations(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    limit: int = 50,
) -> AssistantConversationListResponse:
    """List the caller's (non-archived) assistant conversations, newest first."""
    _require_enabled()
    convs = conversation_store.list_conversations(db_session, current_user, limit=limit)
    return AssistantConversationListResponse(
        items=[
            AssistantConversationSummary(
                id=c.id,
                title=c.title,
                company_id=c.company_id,
                message_count=len(c.messages),
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in convs
        ]
    )


@assistant_router.get(
    "/conversations/{conversation_id}",
    response_model=AssistantConversationDetailResponse,
)
def get_conversation(
    conversation_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AssistantConversationDetailResponse:
    """Get one of the caller's conversations with its full transcript (owner-scoped; 404 otherwise)."""
    _require_enabled()
    conv = conversation_store.get_conversation(db_session, current_user, conversation_id)
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return AssistantConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        company_id=conv.company_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            AssistantPersistedMessage(
                id=m.id,
                role=m.role.value,
                content=m.content,
                used_tools=m.used_tools or [],
                action_cards=m.action_cards or [],
                model=m.model,
                created_at=m.created_at,
            )
            for m in conv.messages
        ],
    )


@assistant_router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_conversation(
    conversation_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> None:
    """Soft-archive one of the caller's conversations (owner-scoped; 404 otherwise)."""
    _require_enabled()
    archived = conversation_store.archive_conversation(
        db_session, current_user, conversation_id
    )
    if not archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
