"""Integration tests for /api/telemetry/v2/catalog."""
from unittest.mock import Mock

from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from tests.conftest import test_app


def _bypass_auth():
    user = Mock(spec=CurrentUserSchema)
    user.id = 1
    user.is_system_user = True
    user.role = Mock()
    user.role.permissions = {}
    user.get_limited_companies_ids = lambda: []
    user.get_limited_sites_ids = lambda: []
    return user


class TestCatalogEndpoint:
    def test_unauthenticated_returns_401(self, client):
        response = client.get("/api/telemetry/v2/catalog")
        assert response.status_code == 401

    def test_authenticated_returns_seeded_providers(self, client):
        test_app.dependency_overrides[get_current_user] = _bypass_auth
        try:
            response = client.get("/api/telemetry/v2/catalog")
            assert response.status_code == 200, response.text
            body = response.json()
            assert "items" in body
            keys = {item["provider_key"] for item in body["items"]}
            # Catalog seed (ff18 migration) should include the two phase-1 vendors.
            assert {"also_energy", "kmc"}.issubset(keys)
            for item in body["items"]:
                assert "id" in item
                assert "display_name" in item
                assert "is_enabled" in item
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)
