from app.settings import settings


class TestSitesWeatherUpdateProcess:

    SITES_ENDPOINT = "/api/internal/sites"

    def _gen_site_actual_production_chart_endpoint(self, _site_id):
        return f"/api/operations-and-maintenance/sites/{_site_id}/actual-production-chart"

    def test_site_weather_update_flow(
        self, client, site_id, system_user_auth_header, mocked_big_query_site_actual_production_data
    ):
        """Test that update weather steps works correctly from fetching site ids to site weather update"""
        # first retrieve sites with locations for weather update
        sites_locations_response = client.get(
            f"{self.SITES_ENDPOINT}/locations",
            params={"api_key": settings.api_key},
        )
        # simulate sites update by info from weather provider
        update_sites_payload = []
        for site in sites_locations_response.json()["data"]:
            update_sites_payload.append(
                {
                    "site_id": site["id"],
                    "weather_description": "Sunny",
                    "weather_icon_url": "http://weather.com/sunny.png",
                }
            )
        update_response = client.post(
            f"{self.SITES_ENDPOINT}/weather",
            params={"api_key": settings.api_key},
            json={"payload": update_sites_payload},
        )
        assert update_response.status_code == 201
        # update second time to have multiple weather rows
        update_sites_payload_2 = []
        for site in sites_locations_response.json()["data"]:
            update_sites_payload_2.append(
                {
                    "site_id": site["id"],
                    "weather_description": "Cloudy",
                    "weather_icon_url": "http://weather.com/cloudy.png",
                }
            )
        update_response_2 = client.post(
            f"{self.SITES_ENDPOINT}/weather",
            params={"api_key": settings.api_key},
            json={"payload": update_sites_payload_2},
        )
        assert update_response_2.status_code == 201
        # validate site is returned with the latest weather update
        response = client.get(
            self._gen_site_actual_production_chart_endpoint(site_id),
            headers=system_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["weather"] == {
            "weather_description": "Cloudy",
            "weather_icon_url": "http://weather.com/cloudy.png",
        }
