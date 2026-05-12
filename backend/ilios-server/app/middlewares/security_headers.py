"""Security headers middleware.

Adds conservative browser security defaults to every response:
    - Strict-Transport-Security
    - X-Content-Type-Options
    - X-Frame-Options
    - Referrer-Policy
    - Permissions-Policy (conservative)

A strict Content-Security-Policy is deliberately NOT set here; CSP requires
verifying the React/MUI bundle behavior end-to-end and is reserved for a
later hardening sprint.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)
        for header, value in _HEADERS.items():
            response.headers.setdefault(header, value)
        return response
