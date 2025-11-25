from app.settings import settings


class TestRedisInternalEndpoints:

    @staticmethod
    def _generate_redis_cache_endpoint():
        return f"/api/internal/cleanup-cache"

    def test_cleanup_redis_cache(self, client, mocker):
        cache_mock = mocker.patch("app.routers.internal.redis.get_cache")
        response = client.post(self._generate_redis_cache_endpoint(), params={"api_key": settings.api_key})
        assert response.status_code == 202
        assert response.json()["message"] == "Redis cache cleared"
        cache_mock.return_value.flushdb.assert_called_once()

    def test_cleanup_redis_cache_403(self, client, mocker):
        mocker.patch("app.routers.internal.redis.get_cache")
        response = client.post(self._generate_redis_cache_endpoint(), params={"api_key": "21223243"})
        assert response.status_code == 403
