from collections.abc import Iterator

from ..common.entities import TelemetryAlertPayload, TelemetryPointPayload
from ..common.enums import DataProvider
from ..common.params import FetchTelemetryDataJobRequestParams
from .data_providers import also_energy, kmc


def fetch_telemetry_points(params: FetchTelemetryDataJobRequestParams) -> Iterator[TelemetryPointPayload]:
    match params.data_provider:
        case DataProvider.ALSO_ENERGY:
            return also_energy.fetch_telemetry_points(params.token, params.site_id, params.device_id)
        case DataProvider.KMC:
            return kmc.fetch_telemetry_points(params.token, params.site_id, params.device_id)
        case _:
            data_provider = str(params.data_provider)
            raise NotImplementedError(f"{data_provider=}")


def fetch_telemetry_alerts(params: FetchTelemetryDataJobRequestParams) -> Iterator[TelemetryAlertPayload]:
    match params.data_provider:
        case DataProvider.ALSO_ENERGY:
            return also_energy.fetch_telemetry_alerts(params.token, params.site_id, params.device_id)
        case DataProvider.KMC:
            return kmc.fetch_telemetry_alerts(params.token, params.site_id, params.device_id)
        case _:
            data_provider = str(params.data_provider)
            raise NotImplementedError(f"{data_provider=}")
