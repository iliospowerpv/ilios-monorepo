import base64
from http import HTTPStatus

import requests

from ...common import request
from ...common.constants import DATA_PROVIDER_API_URLS, MAX_RETRIES_PER_REQUEST, TIMEOUT_PER_REQUEST
from ...common.enums import DataProvider
from ...common.retrying import retry_on_exception
from ...common.validation import validate_response_status

API_URL = DATA_PROVIDER_API_URLS[DataProvider.ALSO_ENERGY]


def verify_token(token: str) -> bool:
    username, password = _decode_basic_auth_token(token)
    response = _get_token_request(username, password)
    return response.status_code != HTTPStatus.BAD_REQUEST


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_token_request(username: str, password: str) -> requests.Response:
    response = request.post(
        f"{API_URL}/Auth/token",
        data={
            "grant_type": "password",
            "username": username,
            "password": password,
        },
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.BAD_REQUEST})


def _decode_basic_auth_token(token: str) -> tuple[str, str]:
    return tuple(base64.b64decode(token.encode("utf-8")).decode("utf-8").split(":", 1))  # noqa
