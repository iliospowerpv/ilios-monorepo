from datetime import datetime
from typing import TypedDict

from ..common.enums import DataProvider, PlatformEnvironment, PointTag


class Site(TypedDict):
    id: str
    name: str


class Device(TypedDict):
    id: str
    name: str


class DeviceInfo(TypedDict):
    id: str
    name: str
    category: str | None
    serial_number: str | None
    gateway_id: str | None
    function_id: str | None
    driver: str | None
    last_update_ts: datetime | None


class TelemetryConfigConnection(TypedDict):
    id: int
    data_provider: DataProvider
    token_secret_id: str


class TelemetryConfigDevice(TypedDict):
    id: int
    external_id: str


class TelemetryConfigSite(TypedDict):
    id: int
    external_id: str
    connection_id: int
    devices: list[TelemetryConfigDevice]


class TelemetryConfigCompany(TypedDict):
    id: int
    connections: list[TelemetryConfigConnection]
    sites: list[TelemetryConfigSite]


TelemetryConfig = TelemetryConfigCompany  # alias


class PlatformPayload(TypedDict):
    environment: PlatformEnvironment
    company_id: int
    site_id: int
    device_id: int


class FetchTelemetryDataJobRequestPayload(TypedDict):
    data_provider: DataProvider
    token_secret_id: str
    site_id: str
    device_id: str
    platform: PlatformPayload


class TelemetryPointPayload(TypedDict):
    data_provider: DataProvider
    site_id: str
    device_id: str
    point_tag: PointTag
    point_data_value: int | float
    point_data_ts: datetime
    fetch_ts: datetime


class TelemetryAlertPayload(TypedDict):
    data_provider: DataProvider
    site_id: str
    device_id: str
    alert_id: str
    alert_type: str
    alert_severity: str
    alert_message: str
    alert_is_resolved: bool
    alert_start_ts: datetime
    fetch_ts: datetime
