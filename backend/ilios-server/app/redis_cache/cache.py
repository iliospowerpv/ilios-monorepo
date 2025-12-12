import redis

from app.settings import settings

rd = redis.Redis.from_url(settings.redis_connection_string)


def get_cache():
    return rd
