import logging
from datetime import datetime, timezone

from fastapi import Request

from app.crud.audit_log import AuditLogCRUD
from app.db.session import get_session
from app.middlewares.common import RequestsResponseMiddleware
from app.settings import settings

logger = logging.getLogger(__name__)


AUDIT_SOURCES_AND_ACTIONS_MAP_BY_ENDPOINT = {
    "/api/auth/login": {
        "POST": {
            "source": "Authentication",
            "action": "Login",
        },
        "DELETE": {
            "source": "Authentication",
            "action": "Logout",
        },
    },
}


class AuditingMiddleware(RequestsResponseMiddleware):
    """Create record in the audit table for the tracked endpoints,
    described in the AUDIT_SOURCES_AND_ACTIONS_MAP_BY_ENDPOINT dict.
    The configuration is possible by setting the following environment variables:
    - enable_audit_logger - bool, True by default; if set to False request will go straight-forward without auditing"""

    def __init__(self, app):
        self.db_session = next(get_session())
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if not settings.enable_audit_logger:
            return await call_next(request)

        response, parsed_response_body = await self.process_request(request, call_next)

        self.save_user_audit_log_to_db(request, response, parsed_response_body=parsed_response_body)

        return response

    def save_user_audit_log_to_db(self, request, response, parsed_response_body) -> int | None:
        """Writes user audit logs to the database for the supported endpoints.

        On architecture lvl it is agreed to have audit of real users only, so wrong email attempts to login do not
        count and shouldn't have audit logs. Server's stdout logs are enough for this case.
        """
        supported_endpoint = AUDIT_SOURCES_AND_ACTIONS_MAP_BY_ENDPOINT.get(request.url.path, {}).get(request.method)
        if not supported_endpoint:
            return
        source, action = supported_endpoint["source"], supported_endpoint["action"]

        is_success, details = True, None
        if response.status_code >= 400:
            is_success = False
            # some duplication is provided by our endpoints responses. fastapi already provides status code and
            # message, but we additionally return another obj with status code and msg in the response.message
            details = parsed_response_body["message"] if parsed_response_body else None

        # request.user may be available if we use AuthenticationMiddleware https://www.starlette.io/authentication/
        # For now we can rely on starlette's feature request.state:
        current_user_id = getattr(request.state, "current_user_id", None)
        if not current_user_id:
            return

        audit_log_payload = {
            "source": source,
            "action": action,
            "is_success": is_success,
            "details": details,
            "user_id": current_user_id,
            "created_at": datetime.now(timezone.utc),
        }

        audit_log = AuditLogCRUD(self.db_session).create_item(audit_log_payload)
        audit_log_id = audit_log.id
        # TODO: consider introducing and using global request id, see IOSP1-934:
        response.headers.update({"X-Request-Audit-Id": str(audit_log_id)})

        audit_log_payload.update({"audit_log_id": audit_log_id})
        logger.debug(f"Added audit log record: {audit_log_payload}")

        return audit_log_id
