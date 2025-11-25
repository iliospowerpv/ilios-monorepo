import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends

from app.crud.chatbot import ChatBotConversationsCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import AuthorizedUser, DiligencePermissions
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.chatbot.session_maker import ChatBotSessionMaker
from app.models.session import Session
from app.models.site import Site
from app.schema.chatbot import ChatbotSessionTokenSchema
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions

logger = logging.getLogger(__name__)
chatbot_router = APIRouter()


@chatbot_router.get(
    "/session-token",
    response_model=ChatbotSessionTokenSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(DiligencePermissions(PermissionsActions.view)))],
)
async def get_session_token(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    chatbot_session_payload = {"user_id": current_user.id, "site_id": site.id, "company_id": site.company_id}
    token, conversation_id = ChatBotSessionMaker().get_session_token(chatbot_session_payload)
    conversation_crud = ChatBotConversationsCRUD(db_session)
    conversation = conversation_crud.get_by_conversation_id(site.id, conversation_id)
    if not conversation:
        conversation_crud.create_item({**chatbot_session_payload, "conversation_id": conversation_id})
    else:
        conversation_crud.update_by_id(conversation.id, {"updated_at": datetime.now(timezone.utc)})
    return {"token": token, "session_id": conversation_id}
