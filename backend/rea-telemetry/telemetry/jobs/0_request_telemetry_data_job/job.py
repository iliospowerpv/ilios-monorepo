from collections.abc import Iterator

from .common.entities import FetchTelemetryDataJobRequestPayload, PlatformPayload, TelemetryConfig
from .common.enums import PlatformEnvironment


def parse_telemetry_config(
    environment: PlatformEnvironment,
    config: TelemetryConfig,
) -> Iterator[FetchTelemetryDataJobRequestPayload]:
    company = config  # alias

    connection_by_id = {connection["id"]: connection for connection in company["connections"]}

    for site in company["sites"]:
        connection = connection_by_id.get(site["connection_id"])

        if connection is None:
            continue

        for device in site["devices"]:
            yield FetchTelemetryDataJobRequestPayload(
                data_provider=connection["data_provider"],
                token_secret_id=connection["token_secret_id"],
                site_id=site["external_id"],
                device_id=device["external_id"],
                platform=PlatformPayload(
                    environment=environment,
                    company_id=company["id"],
                    site_id=site["id"],
                    device_id=device["id"],
                ),
            )
