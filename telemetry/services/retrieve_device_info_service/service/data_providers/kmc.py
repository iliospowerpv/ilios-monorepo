from http import HTTPStatus

import orjson
import requests

from ...common import request
from ...common.constants import DATA_PROVIDER_API_URLS, MAX_RETRIES_PER_REQUEST, TIMEOUT_PER_REQUEST
from ...common.entities import DeviceInfo
from ...common.enums import DataProvider
from ...common.exceptions import DeviceNotFoundError, SiteNotFoundError, TokenUnauthorizedError
from ...common.retrying import retry_on_exception
from ...common.validation import validate_response_status

API_URL = DATA_PROVIDER_API_URLS[DataProvider.KMC]


def retrieve_device_info(token: str, site_id: str, device_id: str) -> DeviceInfo:
    token = _get_site_token(token, site_id)

    response = _get_devices_request(token)

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise TokenUnauthorizedError("Token Unauthorized")

    payload = orjson.loads(response.content)

    try:
        device_item = next(
            device_item
            for device_item in map(lambda item: item["tags"], payload["results"])
            if device_item["id"] == device_id
        )
    except StopIteration:
        raise DeviceNotFoundError("Device Not Found")

    return DeviceInfo(
        id=device_item["id"],
        name=device_item["dis"],
        category=None,
        serial_number=None,
        gateway_id=None,
        function_id=None,
        driver=None,
        last_update_ts=None,
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
