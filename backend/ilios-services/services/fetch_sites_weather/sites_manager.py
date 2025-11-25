import requests
from .common import cloud_logging
from .common.settings import settings


logger = cloud_logging.get_logger(__name__)


class SitesManager:
    def __init__(self):
        cloud_logging.setup()
        self.sites_url = f"{settings.base_platform_api_url}/internal/sites"

    def fetch_sites_locations(self):
        url = f"{self.sites_url}/locations"
        logger.info(f"Fetching site locations from {url}")
        response = requests.get(url, params={"api_key": settings.api_key})
        if response.status_code != 200:
            logger.error(
                f"Failed to fetch site locations from {self.sites_url}, status_code: {response.status_code}, "
                f"error: {response.json()["message"]}"
            )
            return []
        logger.info(f"Fetched site locations: {response.json()["data"]}")
        return response.json()["data"]

    def update_sites_weather(self, payload):
        logger.info(f"Updating platform sites weather...")
        url = f"{self.sites_url}/weather"
        response = requests.post(url, params={"api_key": settings.api_key}, json={"payload": payload})
        if response.status_code != 201:
            logger.error(
                f"Failed to update sites weather, status_code: {response.status_code}, "
                f"error: {response.json()["message"]}"
            )
        else:
            logger.info(f"Updated platform sites weather.")

    def get_site_weather_from_provider(self, site_id, site_location: str):
        logger.info(f"Fetching site weather from provider for site_id: {site_id}, location {site_location}")
        params = {"access_key": settings.weather_provider_access_key, "query": site_location}
        response = requests.get(settings.current_weather_api_url, params=params)
        response_json = response.json()
        if response_json.get("current"):
            return response_json["current"]
        if response_json.get("error"):
            logger.error(
                f"Failed to fetch weather data from provider for site_id: {site_id}, "
                f"error: '{response.json()["error"]["info"]}'"
            )

    def process_sites_weather(self):
        update_payload = []
        sites_locations = self.fetch_sites_locations()
        for site in sites_locations:
            weather_provider_response = self.get_site_weather_from_provider(site["id"], site["location"])
            if weather_provider_response:
                weather_description, weather_icon_url = (
                    weather_provider_response["weather_descriptions"][0],
                    weather_provider_response["weather_icons"][0],
                )
            else:
                weather_description = weather_icon_url = "N/A"
            update_payload.append(
                {
                    "site_id": site["id"],
                    "weather_description": weather_description,
                    "weather_icon_url": weather_icon_url,
                }
            )
        if update_payload:
            self.update_sites_weather(update_payload)
