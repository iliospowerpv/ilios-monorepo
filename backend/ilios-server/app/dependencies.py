import logging

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

AUTH_HEADER_NAME = "Authorization"
auth_header = APIKeyHeader(name=AUTH_HEADER_NAME, auto_error=False)


def validate_auth_header(request: Request, auth_header_value: str = Security(auth_header)):  # noqa: U100
    if auth_header_value is None:
        logger.error("Missing 'Authorization' header.")
        raise HTTPException(status_code=401)

    if not isinstance(auth_header_value, str):
        logger.error(
            f"Expected string for the 'Authorization' header, got '{auth_header_value}'  ({type(auth_header_value)})."
        )
        raise HTTPException(status_code=401)

    auth_header_parts = auth_header_value.split(" ")
    if not len(auth_header_parts) == 2:
        logger.error(f"Expected 'Authorization' header in the format 'Bearer JWT', got '{auth_header_value}'.")
        raise HTTPException(status_code=401)

    token_type, access_token = auth_header_parts

    if not str(token_type).lower() == "bearer":
        logger.error(f"Expected 'Authorization' header to be Bearer, got '{token_type}'.")
        raise HTTPException(status_code=401)

    return access_token
