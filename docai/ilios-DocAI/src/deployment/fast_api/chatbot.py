import asyncio
import json
import logging
from typing import Annotated, Any
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer

from src.chatbot.config import ChatbotConfig
from src.chatbot.modules.base import ChatbotBase
from src.chatbot.modules.messages import welcome_message
from src.deployment.fast_api.auth import api_key_check
from src.deployment.fast_api.connection_manager import ConnectionManager
from src.deployment.fast_api.models.auth import AuthRequest, AuthResponse, Token
from src.deployment.fast_api.models.chatbot_status import ChatbotState, ResponseStatus
from src.deployment.fast_api.settings import settings
from src.deployment.fast_api.utils import (
    generate_session_id,
    generate_token,
    parse_chatbot_response,
)
from src.gen_ai.gen_ai import get_llm


chatbot_router = APIRouter(tags=["chatbot"], prefix="/chatbot")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
manager = ConnectionManager()
llm = get_llm(model_type="CLAUDE")
logger = logging.getLogger(__name__)


@chatbot_router.post(
    "/get_token", response_model=AuthResponse, dependencies=[Depends(api_key_check)]
)
async def chatbot_handshake(auth_request: AuthRequest) -> AuthResponse:
    logger.info(f"Auth request: {auth_request}")
    try:
        token = generate_token(
            auth_request.user_id, auth_request.company_id, auth_request.site_id
        )
        session_id = generate_session_id(
            auth_request.user_id, auth_request.company_id, auth_request.site_id
        )
        return AuthResponse(
            token=Token(access_token=token, token_type="bearer"), session_id=session_id
        )
    except Exception as e:
        logger.info(f"Error: {str(e)}")
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> Any:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        logger.info(f"Decoded payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@chatbot_router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket, token: str) -> None:
    logger.info(f"Token: {token}")
    try:
        user = get_current_user(token)
    except Exception as e:
        logger.info(f"Error: {str(e)}")
        raise HTTPException(status_code=401, detail=str(e))
    await websocket.accept()
    await asyncio.sleep(0)
    user_id = user["user_id"]
    site_id = user["site_id"]
    company_id = user["company_id"]
    manager.connect(websocket, user_id, site_id, company_id)
    await asyncio.sleep(0)
    await manager.send_personal_message(
        json.dumps(
            parse_chatbot_response(
                welcome_message, {"status": ResponseStatus.COMPLETE.value}
            )
        ),
        websocket,
    )
    await asyncio.sleep(0)
    await manager.send_personal_message(
        json.dumps(
            parse_chatbot_response(
                ChatbotState.READY.value, {"status": ResponseStatus.AWAITING_DATA.value}
            )
        ),
        websocket,
    )

    try:
        chatbot = ChatbotBase(
            llm=llm,
            config=ChatbotConfig(
                max_documents=5,
            ),
            site_id=site_id,
            company_id=company_id,
            socket_manager=manager,
            websocket=websocket,
        )

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await manager.send_personal_message(
            json.dumps(
                parse_chatbot_response(
                    ChatbotState.ERROR.value, {"status": ResponseStatus.ERROR.value}
                )
            ),
            websocket,
        )
        await asyncio.sleep(0)
        manager.disconnect(user_id, site_id, company_id)
        return
    try:
        while True:
            await asyncio.sleep(0)
            try:
                data = await websocket.receive_text()
                await asyncio.sleep(0)
                logger.info(f"Data received: {data}")
            except WebSocketDisconnect as e:
                logger.error(f"Websocket disconnect while receiving data: {str(e)}")
                try:
                    chatbot.persist_history(
                        user_id, site_id, company_id, conversation_id=str(uuid4())
                    )
                except Exception as chatbot_history_error:
                    logger.error(
                        f"Error raised saving chatbot messages history: "
                        f"{str(chatbot_history_error)}"
                    )
                logger.error(f"Websocket disconnect while answering question: {str(e)}")
                manager.disconnect(user_id, site_id, company_id)
                break
            logger.info(f"Data: {data}")
            await asyncio.sleep(0)
            try:
                result = await chatbot.invoke({"human_input": data})
                await asyncio.sleep(0)
                await manager.send_personal_message(
                    json.dumps(
                        parse_chatbot_response(
                            result, {"status": ResponseStatus.COMPLETE.value}
                        )
                    ),
                    websocket,
                )
                await asyncio.sleep(0)
                await manager.send_personal_message(
                    json.dumps(
                        parse_chatbot_response(
                            ChatbotState.READY.value,
                            {"status": ResponseStatus.AWAITING_DATA.value},
                        )
                    ),
                    websocket,
                )
                await asyncio.sleep(0)
            except WebSocketDisconnect as e:
                try:
                    chatbot.persist_history(
                        user_id, site_id, company_id, conversation_id=str(uuid4())
                    )
                except Exception as chatbot_history_error:
                    logger.error(
                        f"Error raised saving chatbot messages history: "
                        f"{str(chatbot_history_error)}"
                    )
                logger.error(f"Websocket disconnect while answering question: {str(e)}")
                manager.disconnect(user_id, site_id, company_id)
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}")
                await manager.send_personal_message(
                    json.dumps(
                        parse_chatbot_response(
                            ChatbotState.ERROR.value,
                            {"status": ResponseStatus.ERROR.value},
                        )
                    ),
                    websocket,
                )
                await asyncio.sleep(0)
                continue
    except WebSocketDisconnect:
        manager.disconnect(user_id, site_id, company_id)
