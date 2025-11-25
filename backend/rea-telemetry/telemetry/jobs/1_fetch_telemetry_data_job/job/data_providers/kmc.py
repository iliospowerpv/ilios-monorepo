import itertools
from collections.abc import Iterator
from datetime import datetime, timezone
from http import HTTPStatus

import orjson
import requests

from ...common import cloud_logging, request
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

API_URL = DATA_PROVIDER_API_URLS[DataProvider.KMC]
POINT_TAG_MAP = DATA_PROVIDER_POINT_TAG_MAPS[DataProvider.KMC]  # internal -> external


def fetch_telemetry_points(token: str, site_id: str, device_id: str) -> Iterator[TelemetryPointPayload]:
    token = _get_site_token(token, site_id)

    _validate_token_device(token, device_id)

    with cache.next_fetch_telemetry_points_intervals_map(DataProvider.KMC, site_id, device_id) as intervals_map:
        point_count = 0

        for point_tag, intervals in intervals_map.items():
            response = _get_points_request(token, device_id, POINT_TAG_MAP[point_tag])

            payload = orjson.loads(response.content)

            if len(payload["results"]) == 0:
                continue

            if len(payload["results"]) != 1:
                logger.warning("Discarding ambiguous device point", device_id=device_id, point_tag=point_tag)
                continue

            point_item = next(map(lambda item: item["tags"], payload["results"]))

            for start_ts, end_ts in intervals:
                fetch_ts = datetime.now(tz=timezone.utc)

                response = _get_point_data_request(token, point_item["id"], start_ts, end_ts)

                payload = orjson.loads(response.content)

                for point_data_item in itertools.chain.from_iterable(
                    map(lambda item: item["trendData"], payload["results"])
                ):
                    point_data_value = _convert_value_to_standard_unit(point_data_item["val"], point_item["unit"])
                    point_data_ts = datetime.fromtimestamp(point_data_item["ts"] / 1_000, tz=timezone.utc)

                    yield TelemetryPointPayload(
                        data_provider=DataProvider.KMC,
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
    token = _get_site_token(token, site_id)

    _validate_token_device(token, device_id)

    alarm_priority_map = {"info": "informational"}

    def map_alarm_priority(priority: str) -> str:
        return alarm_priority_map.get(priority, priority)

    with cache.next_fetch_telemetry_alerts_interval(DataProvider.KMC, site_id, device_id) as (start_ts, end_ts):
        for alarm_tag in ("alarm", "cloudAlarm"):
            response = _get_alarms_request(token, device_id, alarm_tag)

            payload = orjson.loads(response.content)

            for alarm_item in map(lambda item: item["tags"], payload["results"]):
                fetch_ts = datetime.now(tz=timezone.utc)

                response = _get_alarm_instances_request(token, alarm_item["id"])

                payload = orjson.loads(response.content)

                for alarm_instance_item in map(
                    lambda item: item["tags"] | {"⏰": item["createdAt"]},
                    payload["results"],
                ):
                    alert_start_ts = datetime.fromtimestamp(alarm_instance_item["startTime"] / 1_000, tz=timezone.utc)

                    # There may be a delay between when an alarm condition is triggered (i.e., when an alert is started)
                    # and when the corresponding alarm instance (i.e., the relevant alert) is created in the system.
                    alert_create_ts = datetime.fromisoformat(alarm_instance_item.pop("⏰")).astimezone(tz=timezone.utc)

                    if start_ts <= alert_create_ts <= end_ts:
                        alert_id = alarm_instance_item["id"]
                        alert_type = alarm_item["dis"]
                        alert_severity = map_alarm_priority(alarm_item["priority"]).capitalize()
                        alert_message = alarm_item["message"] or ""
                        alert_is_resolved = alarm_instance_item["acknowledged"]

                        yield TelemetryAlertPayload(
                            data_provider=DataProvider.KMC,
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


def _get_site_token(token: str, site_id: str) -> str:
    response = _set_license_request(token, site_id)

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise TokenUnauthorizedError("Token Unauthorized")

    if response.status_code == HTTPStatus.NOT_FOUND:
        raise SiteNotFoundError("Site Not Found")

    payload = orjson.loads(response.content)

    return next(iter(payload["results"]))


def _validate_token_device(token: str, device_id: str) -> None:
    response = _get_devices_request(token)

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise TokenUnauthorizedError("Token Unauthorized")

    payload = orjson.loads(response.content)

    if device_id not in (device_item["id"] for device_item in map(lambda item: item["tags"], payload["results"])):
        raise DeviceNotFoundError("Device Not Found")


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


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_points_request(token: str, device_id: str, point_tag: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/data/objects",
        context={"device_id": device_id, "tag": point_tag},
        params={"q": f"{point_tag} and deviceRef=={device_id}"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response)


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_point_data_request(token: str, point_id: str, start_ts: datetime, end_ts: datetime) -> requests.Response:
    response = request.post(
        f"{API_URL}/api/points/{point_id}/trends",
        context={
            "point_id": point_id,
            "start_ts": start_ts.isoformat(),
            "end_ts": end_ts.isoformat(),
        },
        data=orjson.dumps(
            {
                "start": int(start_ts.timestamp() * 1_000),
                "end": int(end_ts.timestamp() * 1_000),
            }
        ),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response)


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_alarms_request(token: str, device_id: str, alarm_tag: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/data/objects",
        context={"device_id": device_id, "tag": alarm_tag},
        params={"q": f"{alarm_tag} and deviceRef=={device_id}"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response)


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_alarm_instances_request(token: str, alarm_id: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/data/objects",
        context={"alarm_id": alarm_id, "tag": "alarmInstance"},
        params={"q": f"alarmInstance and alarmRef=={alarm_id}"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response)


def _convert_value_to_standard_unit(value: int | float, unit: str) -> int | float:
    match unit:
        case "W":
            value = value / 1_000  # W -> kW
        case "kW/m²":
            value = value * 1_000  # kW -> W
        case "°C":
            value = value * 1.8 + 32  # °C -> °F
    return round(value, 9)
