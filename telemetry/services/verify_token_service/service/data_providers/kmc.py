from http import HTTPStatus

import requests

from ...common import request
from ...common.constants import DATA_PROVIDER_API_URLS, MAX_RETRIES_PER_REQUEST, TIMEOUT_PER_REQUEST
from ...common.enums import DataProvider
from ...common.retrying import retry_on_exception
from ...common.validation import validate_response_status

API_URL = DATA_PROVIDER_API_URLS[DataProvider.KMC]


def verify_token(token: str) -> bool:
    response = _get_user_request(token)
    return response.status_code != HTTPStatus.UNAUTHORIZED


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_user_request(token: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/v2/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.UNAUTHORIZED})
