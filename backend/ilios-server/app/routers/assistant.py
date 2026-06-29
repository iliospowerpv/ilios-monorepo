"""AI Assistant router (Slice 1) — read-only chat endpoint.

``POST /api/assistant/chat`` runs the read-only assistant AS the authenticated caller. The whole
surface is gated behind ``settings.native_assistant_enabled`` (404 when off) so it can roll out
independently of the legacy Due-Diligence chatbot, which it shares nothing with.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.schema.assistant import AssistantChatRequest, AssistantChatResponse
from app.schema.user import CurrentUserSchema
from app.services.assistant.assistant_service import run_assistant_chat
from app.settings import settings

assistant_router = APIRouter()


def _require_enabled() -> None:
    if not settings.native_assistant_enabled:
        # Hidden, not 403: when the flag is off the feature simply does not exist.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


@assistant_router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(
    payload: AssistantChatRequest,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AssistantChatResponse:
    """Answer a single chat turn using the read-only tool catalog. Stateless in Slice 1."""
    _require_enabled()
    return run_assistant_chat(db_session, current_user, payload)
