from http import HTTPStatus

import requests

from ..common import cloud_logging, request, secret_manager
from ..common.constants import (
    MAX_RETRIES_PER_REQUEST,
    PLATFORM_API_KEY_SECRET_NAME,
    PLATFORM_API_URLS,
    PROJECT_ID,
    TIMEOUT_PER_REQUEST,
)
from ..common.params import PlatformParams
from ..common.retrying import retry_on_exception
from ..common.timer import Timer
from ..common.validation import validate_response_status

logger = cloud_logging.get_logger(__name__)


def delete_device(params: PlatformParams) -> None:
    environment = params.environment
    device_id = params.device_id

    api_url = f"{PLATFORM_API_URLS[environment]}/api/internal/devices/{device_id}/deprecate"

    api_key = secret_manager.access_secret(PROJECT_ID, PLATFORM_API_KEY_SECRET_NAME.format(environment=environment))

    sub_logger = logger.bind(environment=environment, api_url=api_url, device_id=device_id)

    sub_logger.info("Deleting device from internal API")

    with Timer() as timer:
        response = _delete_device_request(api_url, api_key)

    status_code = response.status_code
    reason_phrase = HTTPStatus(status_code).phrase

    duration = timer.elapsed_ms / 1_000

    sub_logger.info(
        "Deleted device from internal API",
        status_code=status_code,
        reason_phrase=reason_phrase,
        duration=duration,
    )


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _delete_device_request(api_url: str, api_key: str) -> requests.Response:
    response = request.patch(api_url, params={"api_key": api_key}, timeout=TIMEOUT_PER_REQUEST)
    return validate_response_status(response, expect={HTTPStatus.ACCEPTED, HTTPStatus.NOT_FOUND})
