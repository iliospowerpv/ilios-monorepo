import base64
from http import HTTPStatus

import orjson
import requests

from ...common import request
from ...common.caching import cache_token
from ...common.constants import DATA_PROVIDER_API_URLS, MAX_RETRIES_PER_REQUEST, TIMEOUT_PER_REQUEST
from ...common.entities import Device
from ...common.enums import DataProvider
from ...common.exceptions import SiteNotFoundError, TokenUnauthorizedError
from ...common.retrying import retry_on_exception
from ...common.validation import validate_response_status

API_URL = DATA_PROVIDER_API_URLS[DataProvider.ALSO_ENERGY]


def retrieve_devices(token: str, site_id: str) -> list[Device]:
    token = _get_access_token(token)

    response = _get_devices_request(token, site_id)

    if response.status_code == HTTPStatus.NOT_FOUND:
        raise SiteNotFoundError("Site Not Found")

    if response.status_code == HTTPStatus.NO_CONTENT:
        return []

    payload = orjson.loads(response.content)

    return sorted(
        (
            Device(
                id=str(device_item["id"]),
                name=device_item["name"],
            )
            for device_item in payload["hardware"]
        ),
        key=lambda device: device["name"],
    )


@cache_token
def _get_access_token(token: str) -> str:
    username, password = _decode_basic_auth_token(token)

    response = _get_token_request(username, password)

    if response.status_code == HTTPStatus.BAD_REQUEST:
        raise TokenUnauthorizedError("Token Unauthorized")

    payload = orjson.loads(response.content)

    return payload["access_token"]


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


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_devices_request(token: str, site_id: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/Sites/{site_id}/Hardware",
        context={"site_id": site_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.NOT_FOUND, HTTPStatus.NO_CONTENT})


def _decode_basic_auth_token(token: str) -> tuple[str, str]:
    return tuple(base64.b64decode(token.encode("utf-8")).decode("utf-8").split(":", 1))  # noqa
