import logging
from typing import Optional

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_VARIABLES_FILE = "/etc/secrets/app_values_creds.yaml"

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, extra="ignore")

    # platform config
    api_key: str
    environment_name: str
    base_platform_api_url: Optional[str] = None

    # logging config
    use_cloud_logger: Optional[int] = 1
    project_id: Optional[str] = None

    # weather provider config
    current_weather_api_url: Optional[str] = "https://api.weatherstack.com/current"
    weather_provider_access_key: str

    @field_validator("project_id")
    @classmethod
    def get_project_id(cls, project_id, info) -> tuple:
        return project_id if project_id else f"prj-{info.data.get("environment_name")}-base"


def parse_env_variables() -> dict:
    with open(ENV_VARIABLES_FILE) as stream:
        try:
            return yaml.safe_load(stream)["env_variables"]
        except yaml.YAMLError as exc:
            logger.error(exc)


settings = Settings(**parse_env_variables())
