import base64
from datetime import datetime, timezone
from http import HTTPStatus

import orjson
import requests

from ...common import request
from ...common.caching import cache_token
from ...common.constants import DATA_PROVIDER_API_URLS, MAX_RETRIES_PER_REQUEST, TIMEOUT_PER_REQUEST
from ...common.entities import DeviceInfo
from ...common.enums import DataProvider
from ...common.exceptions import DeviceNotFoundError, SiteNotFoundError, TokenUnauthorizedError
from ...common.retrying import retry_on_exception
from ...common.validation import validate_response_status

API_URL = DATA_PROVIDER_API_URLS[DataProvider.ALSO_ENERGY]


def retrieve_device_info(token: str, site_id: str, device_id: str) -> DeviceInfo:
    token = _get_access_token(token)

    _validate_site_device(token, site_id, device_id)

    response = _get_device_request(token, device_id)

    payload = orjson.loads(response.content)

    device_type_map = {
        "CellModem": "Modem",
        "BatteryBlock": "Battery",
        "Gateway": "Network Gateway",
        "Inverter": "Inverter",
        "ProductionPowerMeter": "Meter",
        "StringCombiner": "Combiner Box",
        "VideoCamera": "Camera",
        "WeatherStation": "Weather Station",
    }

    device_item = payload

    return DeviceInfo(
        id=str(device_item["id"]),
        name=device_item["name"],
        category=device_type_map.get(device_item["config"]["deviceType"]),
        serial_number=device_item.get("serialNumber"),
        gateway_id=device_item.get("gatewayId"),
        function_id=device_item["functionCode"],
        driver=device_item["driver"]["name"],
        last_update_ts=datetime.fromisoformat(device_item["lastUpdate"]).astimezone(tz=timezone.utc),
    )


@cache_token
def _get_access_token(token: str) -> str:
    username, password = _decode_basic_auth_token(token)

    response = _get_token_request(username, password)

    if response.status_code == HTTPStatus.BAD_REQUEST:
        raise TokenUnauthorizedError("Token Unauthorized")

    payload = orjson.loads(response.content)

    return payload["access_token"]


def _validate_site_device(token: str, site_id: str, device_id: str) -> None:
    response = _get_devices_request(token, site_id)

    if response.status_code == HTTPStatus.NOT_FOUND:
        raise SiteNotFoundError("Site Not Found")

    if response.status_code == HTTPStatus.NO_CONTENT:
        raise DeviceNotFoundError("Device Not Found")

    payload = orjson.loads(response.content)

    if device_id not in (str(device_item["id"]) for device_item in payload["hardware"]):
        raise DeviceNotFoundError("Device Not Found")


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


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_device_request(token: str, device_id: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/Hardware/{device_id}",
        context={"device_id": device_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response)


def _decode_basic_auth_token(token: str) -> tuple[str, str]:
    return tuple(base64.b64decode(token.encode("utf-8")).decode("utf-8").split(":", 1))  # noqa
