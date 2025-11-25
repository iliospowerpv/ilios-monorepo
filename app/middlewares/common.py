import json
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AsyncIteratorWrapper:
    """Transform a regular iterable to an asynchronous one"""

    def __init__(self, obj):
        self._it = iter(obj)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            value = next(self._it)
        except StopIteration:
            raise StopAsyncIteration
        return value


class RequestsResponseMiddleware(BaseHTTPMiddleware):
    """Common base for RequestsLoggerMiddleware and AuditingMiddleware:
    checks if middleware is enabled, parses response"""

    def __init__(self, app):
        super().__init__(app)

    async def process_request(self, request: Request, call_next):
        # proceed the request
        response = await call_next(request)

        # collect response related data
        response_body = None
        # process only endpoints started from /api/ prefix
        # skip logging for the OPTIONS method, since it produces a lot of errors:
        # https://softserve-jirasw.atlassian.net/browse/IOSP1-1553
        if (
            request.get("path").startswith("/api/")
            and request.method != "OPTIONS"
            and response.headers.get("content-type") == "application/json"
        ):
            try:
                response_body = [section async for section in response.__dict__["body_iterator"]]
                response.__setattr__("body_iterator", AsyncIteratorWrapper(response_body))
                if response_body:
                    response_body = json.loads(response_body[0].decode())

            except Exception as exc:
                logger.warning(f"Request response middleware unable to parse response data: {str(exc)}", exc_info=True)

        return response, response_body
