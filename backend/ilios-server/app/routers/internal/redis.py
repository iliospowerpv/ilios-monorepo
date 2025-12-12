import logging

from fastapi import APIRouter, Depends, status

from app.helpers.authentication import api_key_check
from app.redis_cache.cache import get_cache, check_redis_health
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_redis_router = APIRouter()


@internal_redis_router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    description="Check Redis connectivity for health monitoring",
)
async def redis_health_check():
    """Health check endpoint for Redis connectivity.
    
    Returns status and message indicating Redis connection health.
    """
    result = check_redis_health()
    status_code = status.HTTP_200_OK if result["status"] == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    return {"code": status_code, **result}


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
