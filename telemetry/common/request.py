import uuid
from http import HTTPStatus
from typing import Any, Literal

import requests

from . import cloud_logging
from .timer import Timer

logger = cloud_logging.get_logger(__name__)


def request(
    method: Literal["GET", "POST", "PATCH"],
    url: str,
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> requests.Response:
    request_id = str(uuid.uuid4())

    sub_logger = logger.bind(request_id=request_id)

    sub_logger.info("Sending request to API", method=method, url=url, context=context)

    with Timer() as timer:
        response = requests.request(method, url, **kwargs)

    status_code = response.status_code
    reason_phrase = HTTPStatus(status_code).phrase

    duration = timer.elapsed_ms / 1_000

    sub_logger.info(
        "Received response from API",
        status_code=status_code,
        reason_phrase=reason_phrase,
        duration=duration,
    )

    return response


def get(url: str, context: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
    return request("GET", url, context=context, **kwargs)


def post(url: str, context: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
    return request("POST", url, context=context, **kwargs)


def patch(url: str, context: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
    return request("PATCH", url, context=context, **kwargs)
