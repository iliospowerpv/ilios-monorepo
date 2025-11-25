from http import HTTPStatus

import orjson
import requests

from ...common import request
from ...common.constants import DATA_PROVIDER_API_URLS, MAX_RETRIES_PER_REQUEST, TIMEOUT_PER_REQUEST
from ...common.entities import Device
from ...common.enums import DataProvider
from ...common.exceptions import SiteNotFoundError, TokenUnauthorizedError
from ...common.retrying import retry_on_exception
from ...common.validation import validate_response_status

API_URL = DATA_PROVIDER_API_URLS[DataProvider.KMC]


def retrieve_devices(token: str, site_id: str) -> list[Device]:
    token = _get_site_token(token, site_id)

    response = _get_devices_request(token)

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise TokenUnauthorizedError("Token Unauthorized")

    payload = orjson.loads(response.content)

    return sorted(
        (
            Device(
                id=device_item["id"],
                name=device_item["dis"],
            )
            for device_item in map(lambda item: item["tags"], payload["results"])
        ),
        key=lambda device: device["name"],
    )


def _get_site_token(token: str, site_id: str) -> str:
    response = _set_license_request(token, site_id)

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise TokenUnauthorizedError("Token Unauthorized")

    if response.status_code == HTTPStatus.NOT_FOUND:
        raise SiteNotFoundError("Site Not Found")

    payload = orjson.loads(response.content)

    return next(iter(payload["results"]))


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _set_license_request(token: str, site_id: str) -> requests.Response:
    response = request.post(
        f"{API_URL}/v2/api/auth/setlicense/{site_id}",
        context={"site_id": site_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.UNAUTHORIZED, HTTPStatus.NOT_FOUND})


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_devices_request(token: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/data/objects",
        context={"tag": "device"},
        params={"q": "device"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.UNAUTHORIZED})
