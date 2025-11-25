import os

from .enums import DataProvider, PlatformEnvironment, PointTag

CLOUD = bool(int(os.getenv("CLOUD", default="1")))

PROJECT_ID = os.getenv("PROJECT_ID", default="prj-ilios-telemetry")

DATA_PROVIDER_API_URLS = {
    DataProvider.ALSO_ENERGY: "https://api.alsoenergy.com",
    DataProvider.KMC: "https://app.kmccommander.com",
}

DATA_PROVIDER_POINT_TAG_MAPS = {
    DataProvider.ALSO_ENERGY: {
        PointTag.DEVICE_POWER_AC: "KwAC:Active_Power",
        PointTag.SITE_CELL_TEMPERATURE: "Temp1:Temp_Module",
        PointTag.SITE_IRRADIANCE: "Sun:POA_Irradiance,Sun2:GHI_Irradiance",
        PointTag.SITE_POWER_AC: "KW:Active_Power",
    },
    DataProvider.KMC: {
        PointTag.DEVICE_POWER_AC: "@ilios:devicePowerAC",
        PointTag.SITE_CELL_TEMPERATURE: "@ilios:siteCellTemperature",
        PointTag.SITE_IRRADIANCE: "@ilios:siteIrradiance",
        PointTag.SITE_POWER_AC: "@ilios:sitePowerAC",
    },
}

SECRET_ID_PATTERN = (
    r"^projects/(?P<project_id>[a-z][a-z0-9-]{4,28}[a-z0-9]|[1-9][0-9]*)"
    r"/secrets/(?P<secret_name>[a-zA-Z0-9_-]{1,255})"
    r"(?:/versions/(?P<version_id>latest|[1-9][0-9]*))?$"
)

TELEMETRY_CONFIG_COLLECTION_ID = "{environment}-telemetry-config"
TELEMETRY_CACHE_COLLECTION_ID = "telemetry-cache"

FETCH_TELEMETRY_DATA_TOPIC_NAME = os.getenv("FETCH_TELEMETRY_DATA_TOPIC_NAME", default="fetch-telemetry-data-topic")
INGEST_TELEMETRY_DATA_TOPIC_NAME = os.getenv("INGEST_TELEMETRY_DATA_TOPIC_NAME", default="ingest-telemetry-data-topic")

FETCH_TELEMETRY_DATA_TOPIC_ID = f"projects/{PROJECT_ID}/topics/{FETCH_TELEMETRY_DATA_TOPIC_NAME}"
INGEST_TELEMETRY_DATA_TOPIC_ID = f"projects/{PROJECT_ID}/topics/{INGEST_TELEMETRY_DATA_TOPIC_NAME}"

PLATFORM_API_URLS = {
    PlatformEnvironment.UAT: "https://backend-dot-prj-uat-base-70ab.uc.r.appspot.com",
    PlatformEnvironment.QA: "https://backend-dot-prj-qa-base-23d1.uc.r.appspot.com",
    PlatformEnvironment.DEV: "https://backend-dot-prj-dev-base-e61d.uw.r.appspot.com",
}

PLATFORM_API_KEY_SECRET_NAME = "{environment}-platform-api-key"

MAX_HISTORY_DEPTH_YEARS = 3
MAX_FETCH_INTERVAL_DAYS = 31

MAX_RETRIES_PER_REQUEST = 4
TIMEOUT_PER_REQUEST = 15

LOCK_CACHE_TTL = 2.5 * 60
TOKEN_CACHE_TTL = 10 * 60
