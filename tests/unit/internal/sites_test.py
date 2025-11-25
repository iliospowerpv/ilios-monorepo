from app.settings import settings


class TestSitesInternalEndpoints:
    SITES_ENDPOINT = "/api/internal/sites"

    def test_get_sites_locations(self, client, sites):
        """Test that endpoint returns all sites with locations"""
        expected_response = [{"id": site.id, "location": site.lon_lat_url} for site in sites]
        response = client.get(
            f"{self.SITES_ENDPOINT}/locations",
            params={"api_key": settings.api_key},
        )

        assert response.status_code == 200
        assert response.json()["data"] == expected_response

    def test_create_sites_weather(self, client, site_id):
        """Test that endpoint returns all sites with locations"""
        payload = {
            "payload": [{"site_id": site_id, "weather_description": "Sunny", "weather_icon_url": "http://weather.com"}]
        }
        response = client.post(
            f"{self.SITES_ENDPOINT}/weather",
            params={"api_key": settings.api_key},
            json=payload,
        )
        assert response.status_code == 201
