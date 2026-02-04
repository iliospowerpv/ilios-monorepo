"""Admin routers package."""

from .access_health import access_health_router
from .extraction_registry import extraction_registry_router

__all__ = ["access_health_router", "extraction_registry_router"]
