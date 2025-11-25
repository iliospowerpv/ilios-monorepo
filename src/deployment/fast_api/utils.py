import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt


logger = logging.getLogger(__name__)
SECRET_KEY = str(os.environ.get("SECRET_KEY"))


def generate_token(user_id: int, company_id: int, site_id: int) -> Any:
    """Generate a JWT token for the user."""
    payload = {"user_id": user_id, "company_id": company_id, "site_id": site_id}
    expire = datetime.now(timezone.utc) + timedelta(hours=6)
    payload.update({"exp": expire})  # type: ignore
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    logger.info("Token created")
    return token


def generate_session_id(user_id: int, company_id: int, site_id: int) -> str:
    namespace = uuid.UUID("12345678-1234-5678-1234-567812345678")
    unique_string = f"{str(user_id)}-{str(company_id)}-{str(site_id)}"
    session_id = uuid.uuid5(namespace, unique_string)
    logger.info(f"Session ID created: {str(session_id)}")
    return str(session_id)


def parse_chatbot_response(
    response: Any, metadata: Dict[str, Any]
) -> Dict[str, str | Dict[str, str]]:
    """Parse the chatbot response and return the response message."""
    return {
        "response": str(response),
        "metadata": {key: str(value) for key, value in metadata.items()},
    }
