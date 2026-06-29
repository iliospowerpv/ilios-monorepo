import logging
import traceback

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exception: HTTPException):  # noqa: U100
    return JSONResponse(
        status_code=exception.status_code,
        content={
            "message": str(exception.detail),
            "code": exception.status_code,
        },
        # Propagate any explicitly-set response headers (e.g. Retry-After on a 429,
        # WWW-Authenticate on a 401). Mirrors FastAPI's default handler; None for most errors.
        headers=getattr(exception, "headers", None),
    )


async def validation_exception_handler(request: Request, exception: RequestValidationError):  # noqa: U100
    """Build user-friendly validation error message"""
    msg = "; ".join(
        [f"{'.'.join(str(loc_) for loc_ in error_['loc'])} - {error_['msg']}" for error_ in exception.errors()]
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": f"Validation error: {msg}", "code": status.HTTP_422_UNPROCESSABLE_ENTITY},
    )


async def http_500_exception_handler(request: Request, exception: Exception):  # noqa: U100
    logger.error(f"An exception appeared: {traceback.format_exc()}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal Server Error",
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )
