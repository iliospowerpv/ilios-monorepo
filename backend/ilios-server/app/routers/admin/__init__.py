"""Admin routers package."""

from .access_health import access_health_router
from .auth_security import auth_security_events_router
from .extraction_registry import extraction_registry_router
from .global_admin import global_admin_router

__all__ = [
    "access_health_router",
    "auth_security_events_router",
    "extraction_registry_router",
    "global_admin_router",
]
