"""AI Assistant router — read-only chat + isolated conversation persistence.

The whole surface is gated behind ``settings.native_assistant_enabled`` (404 when off) so it can roll
out independently of the legacy Due-Diligence chatbot, which it shares nothing with. ``POST /chat``
runs the read-only assistant AS the authenticated caller; conversation persistence (when requested)
writes ONLY to the isolated ``assistant_conversations`` tables. Every conversation read/write is
owner-scoped to the current user.
"""
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.schema.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConfigResponse,
    AssistantContextHints,
    AssistantConversationDetailResponse,
    AssistantConversationListResponse,
    AssistantConversationSummary,
    AssistantFeedbackRequest,
    AssistantFeedbackResponse,
    AssistantPersistedMessage,
    AssistantSuggestedPrompt,
    AssistantSuggestedPromptsResponse,
    AssistantUsageResponse,
)
from app.schema.user import CurrentUserSchema
from app.services.assistant import (
    conversation_store,
    llm_client,
    suggested_prompts,
    usage_service,
)
from app.services.assistant.assistant_service import run_assistant_chat
from app.services.assistant.llm_client import AssistantLLMError, AssistantRateLimitError
from app.services.assistant.navigator_suggestions import build_navigator_cards
from app.services.assistant.tools import ALLOWED_TOOLS
from app.services.workflows.orchestration_context_service import PROHIBITED_ACTIONS
from app.settings import settings

assistant_router = APIRouter()


def _require_enabled() -> None:
    if not settings.native_assistant_enabled:
        # Hidden, not 403: when the flag is off the feature simply does not exist.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


def _require_admin(current_user) -> None:
    """Admin gate for observability. Mirrors the existing global-admin pattern (system user OR
    global admin). Runs AFTER the flag check, so flag-off still 404s and only real admins pass."""
    if not getattr(current_user, "has_platform_bypass", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global admin privilege required.",
        )


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

    try:
        response = run_assistant_chat(db_session, current_user, payload)
    except AssistantRateLimitError as exc:
        # Surface a friendly 429 with Retry-After (already in CORS expose_headers) so the FE can show
        # a calibrated "assistant is busy" message and offer a retry.
        headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The assistant is busy right now. Please try again in a moment.",
            headers=headers,
        )
    except AssistantLLMError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The assistant is temporarily unavailable. Please try again shortly.",
        )

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

    assistant_message = conversation_store.append_turn(
        db_session,
        conv,
        user_message=payload.message,
        reply=response.reply,
        used_tools=[t.model_dump(mode="json") for t in response.used_tools],
        action_cards=[c.model_dump(mode="json") for c in response.action_cards],
        sources=[s.model_dump(mode="json") for s in response.sources],
        model=response.model,
    )
    response.conversation_id = str(conv.id)
    response.message_id = assistant_message.id
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
                sources=m.sources or [],
                action_cards=m.action_cards or [],
                model=m.model,
                feedback=m.feedback.value if m.feedback else None,
                feedback_note=m.feedback_note,
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


@assistant_router.post(
    "/conversations/{conversation_id}/messages/{message_id}/feedback",
    response_model=AssistantFeedbackResponse,
)
def set_message_feedback(
    conversation_id: int,
    message_id: int,
    payload: AssistantFeedbackRequest,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AssistantFeedbackResponse:
    """Set/clear thumbs feedback on one of the caller's ASSISTANT messages (owner-scoped).

    Writes ONLY to the isolated assistant message row — never a governed/business action. A
    cross-user or user-message/non-existent target resolves to 404 (never reveals another's data).
    """
    _require_enabled()
    message = conversation_store.set_feedback(
        db_session,
        current_user,
        conversation_id=conversation_id,
        message_id=message_id,
        rating=payload.rating,
        note=payload.note,
    )
    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Message not found"
        )
    return AssistantFeedbackResponse(
        message_id=message.id,
        feedback=message.feedback.value if message.feedback else None,
        feedback_note=message.feedback_note,
    )


@assistant_router.get(
    "/suggested-prompts", response_model=AssistantSuggestedPromptsResponse
)
def get_suggested_prompts(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    route: Optional[str] = None,
    site_id: Optional[int] = None,
    company_id: Optional[int] = None,
) -> AssistantSuggestedPromptsResponse:
    """Return static, page-aware example prompts PLUS proactive, route-aware navigator cards.

    The ``prompts`` are pure static UI affordances (no data fetch). The ``action_cards`` are the
    "global navigator" affordance: deterministic, permission-gated ``explain``/``open``/``resume``
    deep links derived from the current route + scope. Every card is validated read-only and
    fail-closed by ``build_navigator_cards`` (a denied/under-scoped card is simply absent), so this
    endpoint stays zero-mutation and never widens authorization."""
    _require_enabled()
    context_label, prompts = suggested_prompts.get_suggested_prompts(route)
    hints = AssistantContextHints(route=route, site_id=site_id, company_id=company_id)
    action_cards = build_navigator_cards(db_session, current_user, hints)
    return AssistantSuggestedPromptsResponse(
        context_label=context_label,
        prompts=[AssistantSuggestedPrompt(**p) for p in prompts],
        action_cards=action_cards,
    )


@assistant_router.get("/admin/usage", response_model=AssistantUsageResponse)
def admin_usage(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AssistantUsageResponse:
    """Read-only aggregate usage over ONLY the isolated assistant tables. Admin-only (403 otherwise);
    flag-gated (404 when off). Touches no operational/business data and performs no writes."""
    _require_enabled()
    _require_admin(current_user)
    return usage_service.build_usage_summary(db_session)
