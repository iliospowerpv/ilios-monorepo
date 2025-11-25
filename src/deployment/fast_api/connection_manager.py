import json
import logging
from typing import Dict

from fastapi import WebSocket

from src.deployment.fast_api.models.chatbot_status import ChatbotState, ResponseStatus
from src.deployment.fast_api.utils import parse_chatbot_response


logger = logging.getLogger(__name__)


class ConnectionManager:
    """Connection manager class to manage active connections to the Chatbot."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    def connect(
        self, websocket: WebSocket, user_id: int, site_id: int, company_id: int
    ) -> None:
        """Connect a user to the Chatbot. The connection is established based on
        site_id, user_id, and company_id."""
        logger.info(f"Connecting: {user_id}, {site_id}, {company_id}")
        connection_key = f"{user_id}_{site_id}_{company_id}"
        self.active_connections[connection_key] = websocket
        logger.info(f"Connected: {connection_key}")

    def disconnect(self, user_id: int, site_id: int, company_id: int) -> None:
        """Disconnect a user from the Chatbot"""
        logger.info(f"Disconnecting: {user_id}, {site_id}, {company_id}")
        connection_key = f"{user_id}_{site_id}_{company_id}"
        if connection_key in self.active_connections:
            del self.active_connections[connection_key]

    @staticmethod
    async def send_personal_message(message: str, websocket: WebSocket) -> None:
        """Send text response to websocket recipient."""
        logger.info(f"Sending message: {message}")
        await websocket.send_text(message)

    async def broadcast(
        self, message: str, user_id: int, site_id: int, company_id: int
    ) -> None:
        """Broadcast a message to all active connections."""
        connection_key = f"{user_id}_{site_id}_{company_id}"
        if connection_key in self.active_connections:
            await self.active_connections[connection_key].send_text(message)

    async def send_chatbot_status(
        self,
        chatbot_state: ChatbotState,
        response_status: ResponseStatus,
        websocket: WebSocket,
    ) -> None:
        """Send chatbot response status to the recipient."""
        await self.send_personal_message(
            json.dumps(
                parse_chatbot_response(
                    chatbot_state.value, {"status": response_status.value}
                )
            ),
            websocket,
        )
