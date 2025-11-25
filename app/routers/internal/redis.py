import logging

from fastapi import APIRouter, Depends, status

from app.helpers.authentication import api_key_check
from app.redis_cache.cache import get_cache
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_redis_router = APIRouter()


@internal_redis_router.post(
    "/cleanup-cache",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_202_ACCEPTED,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Remove all cached data from Redis cache",
)
async def cleanup_redis_cache():
    cache = get_cache()
    logger.debug("Redis cache cleanup started.")
    logger.debug(f"Keys before cleanup: {cache.keys('*')}")
    cache.flushdb()
    logger.debug(f"Keys after cleanup: {cache.keys('*')}")
    logger.debug("Redis cache cleanup finished.")
    return {"code": status.HTTP_202_ACCEPTED, "message": "Redis cache cleared"}
