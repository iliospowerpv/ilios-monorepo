from fastapi import APIRouter

from .alerts import internal_alerts_router
from .co_terminus_checks import internal_co_terminus_router
from .comments import internal_comments_router
from .configs import internal_configs_router
from .devices import internal_devices_router, internal_telemetry_devices_router
from .documents import internal_documents_router
from .files import internal_files_router
from .redis import internal_redis_router
from .sites import internal_weather_router

internal_router = APIRouter()

# Include all internal routers under 'Internal' tag
internal_router.include_router(internal_comments_router)
internal_router.include_router(internal_devices_router)
internal_router.include_router(internal_documents_router)

# Separate routes related to the AI integration
internal_ai_router = APIRouter()
internal_ai_router.include_router(internal_configs_router)
internal_ai_router.include_router(internal_files_router)
internal_ai_router.include_router(internal_co_terminus_router)

# Separate routes related to the Telemetry integration
internal_telemetry_router = APIRouter()
internal_telemetry_router.include_router(internal_alerts_router)
internal_telemetry_router.include_router(internal_telemetry_devices_router)
internal_telemetry_router.include_router(internal_redis_router)

internal_sites_router = APIRouter()
internal_sites_router.include_router(internal_weather_router)
