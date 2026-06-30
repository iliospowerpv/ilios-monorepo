"""System Settings routers package (superuser-only surfaces).

Groups the read-only operational surfaces exposed under ``/api/settings``:

- ``audit_logs_router``      -> ``/api/settings/audit-logs`` (paginated audit trail read)
- ``service_health_router``  -> ``/api/settings/service-health`` (third-party service status)
- ``architecture_router``    -> ``/api/settings/architecture`` (DB structure + docs reference)

Every endpoint in this package depends on ``get_current_admin_user`` and is
therefore restricted to platform-bypass (system / global admin) users.
"""

from .architecture import architecture_router
from .audit_logs import audit_logs_router
from .service_health import service_health_router

__all__ = [
    "architecture_router",
    "audit_logs_router",
    "service_health_router",
]
