import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.static.tags import HEALTHCHECK_TAG

health_router = APIRouter(tags=[HEALTHCHECK_TAG])


@health_router.get(
    "/health",
    responses={
        200: {
            "description": "Successful response",
            "content": {"application/json": {"example": {"data": "2024-01-29T09:16:45.005961"}}},
        }
    },
)
async def health() -> dict:
    """Health check"""
    logging.debug("health endpoint called")
    return {"data": datetime.now(timezone.utc)}
