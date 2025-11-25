import logging

from fastapi import HTTPException, status

from app.helpers.cloud_function_client import AIServerClient
from app.settings import settings
from app.static import ChatBotMessages

logger = logging.getLogger(__name__)


class ChatBotSessionMaker:
    """Implements API calls for AI to establish chatbot session"""

    @staticmethod
    def get_session_token(payload):
        """Get chatbot session token to establish connection"""

        client = AIServerClient(func_url=settings.chatbot_session_token_function_url)
        response = client.post(payload=payload, use_api_key=True)
        if response.status_code == 200:
            response_json = response.json()
            return response_json["token"], response_json["session_id"]
        else:
            logger.warning("There is an error in the chatbot call, see AI service logs")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ChatBotMessages.ai_api_error)
