import logging
import redis
from typing import Optional

from app.settings import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def _create_redis_client() -> redis.Redis:
    """Create Redis client with proper TLS handling for Upstash.
    
    Supports both redis:// (no TLS) and rediss:// (TLS) connection strings.
    """
    url = settings.redis_connection_string
    if not url:
        raise ValueError("No Redis URL configured. Set REDIS_URL environment variable.")
    
    logger.info(f"Connecting to Redis (TLS: {url.startswith('rediss://')})")
    return redis.Redis.from_url(url, decode_responses=False)


def get_cache() -> redis.Redis:
    """Get the Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = _create_redis_client()
    return _redis_client


def check_redis_health() -> dict:
    """Check Redis connectivity for health checks.
    
    Returns:
        dict with status and optional error message
    """
    try:
        client = get_cache()
        client.set("health_check", "ok", ex=60)
        result = client.get("health_check")
        if result == b"ok":
            return {"status": "healthy", "message": "Redis connection successful"}
        return {"status": "unhealthy", "message": "Unexpected response from Redis"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}
