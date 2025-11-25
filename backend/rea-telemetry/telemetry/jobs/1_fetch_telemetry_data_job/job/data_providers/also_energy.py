import base64
from collections.abc import Iterator
from datetime import datetime, timezone
from http import HTTPStatus

import orjson
import requests

from ...common import cloud_logging, request
from ...common.caching import cache_token
from ...common.constants import (
    DATA_PROVIDER_API_URLS,
    DATA_PROVIDER_POINT_TAG_MAPS,
    MAX_RETRIES_PER_REQUEST,
    TIMEOUT_PER_REQUEST,
)
from ...common.entities import TelemetryAlertPayload, TelemetryPointPayload
from ...common.enums import DataProvider
from ...common.exceptions import DataUnavailableError, DeviceNotFoundError, SiteNotFoundError, TokenUnauthorizedError
from ...common.retrying import retry_on_exception
from ...common.validation import validate_response_status
from .. import cache

logger = cloud_logging.get_logger(__name__)

API_URL = DATA_PROVIDER_API_URLS[DataProvider.ALSO_ENERGY]
POINT_TAG_MAP = DATA_PROVIDER_POINT_TAG_MAPS[DataProvider.ALSO_ENERGY]  # internal -> external


def fetch_telemetry_points(token: str, site_id: str, device_id: str) -> Iterator[TelemetryPointPayload]:
    token = _get_access_token(token)

    point_name_set = _validate_site_device(token, site_id, device_id)

    with cache.next_fetch_telemetry_points_intervals_map(DataProvider.ALSO_ENERGY, site_id, device_id) as intervals_map:
        point_count = 0

        for point_tag, intervals in intervals_map.items():
            point_name_map = dict(point_name_item.split(":") for point_name_item in POINT_TAG_MAP[point_tag].split(","))

            point_name_subset = point_name_set & point_name_map.keys()

            if len(point_name_subset) == 0:
                continue

            if len(point_name_subset) != 1:
                logger.warning("Discarding ambiguous device point", device_id=device_id, point_tag=point_tag)
                continue

            point_name_legacy = next(iter(point_name_subset))
            point_name_standard = point_name_map[point_name_legacy]

            for start_ts, end_ts in intervals:
                fetch_ts = datetime.now(tz=timezone.utc)

                response = _get_point_data_request(token, device_id, point_name_standard, start_ts, end_ts)

                if response.status_code == HTTPStatus.BAD_REQUEST:
                    break

                if response.status_code == HTTPStatus.NO_CONTENT:
                    continue

                payload = orjson.loads(response.content)

                assert len(payload["info"]) == 1

                if payload["info"][0]["name"] != point_name_legacy:  # mismatch
                    break

                for point_data_item in payload["items"]:
                    assert len(point_data_item["data"]) == 1

                    point_data_value = round(value if (value := point_data_item["data"][0]) != "NaN" else 0.0, 9)
                    point_data_ts = datetime.fromisoformat(point_data_item["timestamp"]).astimezone(tz=timezone.utc)

                    yield TelemetryPointPayload(
                        data_provider=DataProvider.ALSO_ENERGY,
                        site_id=site_id,
                        device_id=device_id,
                        point_tag=point_tag,
                        point_data_value=point_data_value,
                        point_data_ts=point_data_ts,
                        fetch_ts=fetch_ts,
                    )
                    point_count += 1

        if point_count == 0:
            # The device may be offline. Raise an exception to avoid updating the cache. This allows future pipeline
            # runs to resume from the point when the data was last available, until the device eventually comes online.
            raise DataUnavailableError("Data Unavailable")


def fetch_telemetry_alerts(token: str, site_id: str, device_id: str) -> Iterator[TelemetryAlertPayload]:
    token = _get_access_token(token)

    _validate_site_device(token, site_id, device_id)

    alert_severity_map = {"Info": "Informational"}

    def map_alert_severity(severity: str) -> str:
        return alert_severity_map.get(severity, severity)

    with cache.next_fetch_telemetry_alerts_interval(DataProvider.ALSO_ENERGY, site_id, device_id) as (start_ts, end_ts):
        fetch_ts = datetime.now(tz=timezone.utc)

        response = _get_alerts_request(token, device_id)

        if response.status_code == HTTPStatus.NO_CONTENT:
            return

        payload = orjson.loads(response.content)

        for alert_item in payload["items"]:
            alert_start_ts = datetime.fromisoformat(alert_item["timestamp"]).astimezone(tz=timezone.utc)

            if start_ts <= alert_start_ts <= end_ts:
                alert_id = str(alert_item["id"])
                alert_type = alert_item["title"]
                alert_severity = map_alert_severity(alert_item["severity"])
                alert_message = alert_item["description"]
                alert_is_resolved = alert_item["isAcknowledged"] or alert_item["isResolved"] or alert_item["isIgnored"]

                yield TelemetryAlertPayload(
                    data_provider=DataProvider.ALSO_ENERGY,
                    site_id=site_id,
                    device_id=device_id,
                    alert_id=alert_id,
                    alert_type=alert_type,
                    alert_severity=alert_severity,
                    alert_message=alert_message,
                    alert_is_resolved=alert_is_resolved,
                    alert_start_ts=alert_start_ts,
                    fetch_ts=fetch_ts,
                )


@cache_token
def _get_access_token(token: str) -> str:
    username, password = _decode_basic_auth_token(token)

    response = _get_token_request(username, password)

    if response.status_code == HTTPStatus.BAD_REQUEST:
        raise TokenUnauthorizedError("Token Unauthorized")

    payload = orjson.loads(response.content)

    return payload["access_token"]


def _validate_site_device(token: str, site_id: str, device_id: str) -> set[str]:
    response = _get_devices_request(token, site_id)

    if response.status_code == HTTPStatus.NOT_FOUND:
        raise SiteNotFoundError("Site Not Found")

    if response.status_code == HTTPStatus.NO_CONTENT:
        raise DeviceNotFoundError("Device Not Found")

    payload = orjson.loads(response.content)

    try:
        device_item = next(device_item for device_item in payload["hardware"] if str(device_item["id"]) == device_id)
    except StopIteration:
        raise DeviceNotFoundError("Device Not Found")

    return set(device_item["fieldsArchived"])


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
        params={"includeArchivedFields": "true"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.NOT_FOUND, HTTPStatus.NO_CONTENT})


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_point_data_request(
    token: str,
    device_id: str,
    point_name: str,
    start_ts: datetime,
    end_ts: datetime,
) -> requests.Response:
    response = request.post(
        f"{API_URL}/v2/Data/BinData",
        context={
            "device_id": device_id,
            "point_name": point_name,
            "start_ts": start_ts.isoformat(),
            "end_ts": end_ts.isoformat(),
        },
        params={
            "from": start_ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "to": end_ts.strftime("%Y-%m-%dT%H:%M:%S"),
            "binSizes": "BinRaw",
        },
        data=orjson.dumps(
            [
                {
                    "hardwareId": device_id,
                    "fieldName": point_name,
                },
            ]
        ),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.BAD_REQUEST, HTTPStatus.NO_CONTENT})


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_alerts_request(token: str, device_id: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/Hardware/{device_id}/Alerts",
        context={"device_id": device_id},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.NO_CONTENT})


def _decode_basic_auth_token(token: str) -> tuple[str, str]:
    return tuple(base64.b64decode(token.encode("utf-8")).decode("utf-8").split(":", 1))  # noqa
