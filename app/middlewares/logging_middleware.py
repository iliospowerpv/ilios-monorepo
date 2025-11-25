import logging
import re
import time

from fastapi import Request

from app.middlewares.common import RequestsResponseMiddleware
from app.settings import settings

logger = logging.getLogger(__name__)


class RequestsLoggerMiddleware(RequestsResponseMiddleware):
    """
    Log request and response data. The configuration is possible by setting the following environment variables

    - enable_requests_logger - bool, True by default; if set to False request will go straight-forward without logging
    - requests_logger_max_response - integer, optional; if unset full response body logs out
    - requests_logger_include_headers - bool, False by default; if set to True will log out request headers
    """

    API_PATTERNS_TO_EXCLUDE = [
        r"^/api/due-diligence/\d+/co-terminus/check$",
        r"^/api/due-diligence/\d+/documents/\d+/files/\d+/parsing/$",
        r"^/api/account/dashboard/notifications/\d+/seen$",
        r"^/api/internal/devices/\d+/deprecate$",
        r"^/api/sites/\d+/devices/\d+/telemetry-details$",
        r"^/api/internal/cleanup-cache$",
    ]

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if not settings.enable_requests_logger:
            return await call_next(request)

        start_time = time.perf_counter()

        # prepare request related data
        log_data = {
            "request_method": request.method,
            "request_path": request.url.path,
            "request_query": request.url.query,
            "requester_ip": request.client.host,
        }

        # parse request body for write http methods
        # exclude some URLs from the request data logging based on the pattern
        skip_request_data_logging = False
        for pattern in self.API_PATTERNS_TO_EXCLUDE:
            if re.match(pattern, str(request.url.path)):
                skip_request_data_logging = True
        if request.method in ["POST", "PUT", "PATCH"] and not skip_request_data_logging:
            try:
                request_body = await request.json()
                log_data["request_body"] = request_body
            except Exception as exc:
                logger.warning(f"Request logging middleware unable to parse request body: {str(exc)}", exc_info=True)

        response, parsed_response_body = await self.process_request(request, call_next)

        if settings.requests_logger_include_headers:
            log_data.update(
                {
                    "request_headers": request.headers.items(),
                    "response_headers": response.headers.items(),
                }
            )

        # limit characters for output payload if required
        parsed_response_body = str(parsed_response_body)
        if settings.requests_logger_max_response and len(parsed_response_body) > settings.requests_logger_max_response:
            parsed_response_body = f"{parsed_response_body[:settings.requests_logger_max_response]}[...]"

        log_data["response_body"] = parsed_response_body

        log_data.update(
            {"response_status_code": response.status_code, "execution_seconds": time.perf_counter() - start_time}
        )

        logger.debug(log_data)
        return response
