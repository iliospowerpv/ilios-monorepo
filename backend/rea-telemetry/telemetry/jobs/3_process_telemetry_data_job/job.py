from collections import defaultdict
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from http import HTTPStatus
from pathlib import Path
from typing import Any

import orjson
import requests
from jinja2 import Template

from .common import bigquery, cloud_logging, firestore, request, secret_manager
from .common.constants import (
    MAX_HISTORY_DEPTH_YEARS,
    MAX_RETRIES_PER_REQUEST,
    PLATFORM_API_KEY_SECRET_NAME,
    PLATFORM_API_URLS,
    PROJECT_ID,
    TELEMETRY_CONFIG_COLLECTION_ID,
    TIMEOUT_PER_REQUEST,
)
from .common.entities import TelemetryConfig
from .common.enums import PlatformEnvironment
from .common.retrying import retry_on_exception
from .common.timer import Timer
from .common.validation import validate_response_status

logger = cloud_logging.get_logger(__name__)


def prepare_id_map() -> None:
    id_map: dict[tuple[str, str, str], set[tuple[str, int, int, int]]] = defaultdict(set)

    for environment in PlatformEnvironment.as_list():
        collection_id = TELEMETRY_CONFIG_COLLECTION_ID.format(environment=environment)

        sub_logger = logger.bind(environment=environment, collection_id=collection_id)

        for document in firestore.database.stream_documents(collection_id):
            sub_logger.info("Parsing config from Firestore", document_id=document.id)

            for key, value in _parse_telemetry_config(environment, document.data):
                id_map[key].add(value)

    table_id = "telemetry_rfn.id_map"

    schema = [
        bigquery.SchemaField(
            "external",
            "RECORD",
            mode="REQUIRED",
            fields=[
                bigquery.SchemaField("data_provider", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("site_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("device_id", "STRING", mode="REQUIRED"),
            ],
        ),
        bigquery.SchemaField(
            "internal",
            "RECORD",
            mode="REQUIRED",
            fields=[
                bigquery.SchemaField("environment", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("company_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("site_id", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("device_id", "INTEGER", mode="REQUIRED"),
            ],
        ),
    ]

    external_fields = ("data_provider", "site_id", "device_id")
    internal_fields = ("environment", "company_id", "site_id", "device_id")

    rows = (
        {
            "external": dict(zip(external_fields, key)),
            "internal": dict(zip(internal_fields, value)),
        }
        for key, values in id_map.items()
        for value in values
    )

    bigquery.engine.replace_table(table_id, schema, rows)


def process_telemetry_points() -> None:
    _refine_telemetry_points()

    environments = PlatformEnvironment.as_list()

    with ThreadPoolExecutor(max_workers=len(environments)) as executor:
        list(executor.map(_process_telemetry_points, environments))  # wait


def process_telemetry_alerts() -> None:
    _refine_telemetry_alerts()

    environments = PlatformEnvironment.as_list()

    with ThreadPoolExecutor(max_workers=len(environments)) as executor:
        list(executor.map(_process_telemetry_alerts, environments))  # wait


def _parse_telemetry_config(
    environment: PlatformEnvironment,
    config: TelemetryConfig,
) -> Iterator[tuple[tuple[str, str, str], tuple[str, int, int, int]]]:
    company = config  # alias

    connection_by_id = {connection["id"]: connection for connection in company["connections"]}

    for site in company["sites"]:
        connection = connection_by_id.get(site["connection_id"])

        if connection is None:
            continue

        for device in site["devices"]:
            key = (str(connection["data_provider"]), site["external_id"], device["external_id"])
            value = (str(environment), company["id"], site["id"], device["id"])
            yield (key, value)


def _refine_telemetry_points() -> None:
    bigquery.engine.execute_query(
        """
        CREATE OR REPLACE TABLE FUNCTION telemetry_rfn.points(start_ts TIMESTAMP, end_ts TIMESTAMP)
        RETURNS TABLE <
            data_provider STRING,
            site_id STRING,
            device_id STRING,
            point_tag STRING,
            point_data_value NUMERIC,
            point_data_ts TIMESTAMP
        > AS (
            SELECT * EXCEPT (fetch_ts, ingest_ts) FROM telemetry_raw.points
            WHERE point_data_ts BETWEEN start_ts AND end_ts
            QUALIFY (
                ROW_NUMBER() OVER (
                    PARTITION BY data_provider, site_id, device_id, point_tag, point_data_ts
                )
            ) = 1
        );
        """
    )


def _process_telemetry_points(environment: PlatformEnvironment) -> None:
    context = {"environment": environment}

    template_dir_path = Path(__file__).parent / "templates"
    template_file_ext = ".sql.jinja2"

    for template_file_path in template_dir_path.glob(f"**/*{template_file_ext}"):
        template = Template(template_file_path.read_text(encoding="utf-8"))

        bigquery.engine.execute_query(template.render(**context))


def _refine_telemetry_alerts() -> None:
    bigquery.engine.execute_query(
        """
        CREATE OR REPLACE TABLE FUNCTION telemetry_rfn.alerts(start_ts TIMESTAMP, end_ts TIMESTAMP)
        RETURNS TABLE <
            data_provider STRING,
            site_id STRING,
            device_id STRING,
            alert_id STRING,
            alert_type STRING,
            alert_severity STRING,
            alert_message STRING,
            alert_is_resolved BOOLEAN,
            alert_start_ts TIMESTAMP
        > AS (
            SELECT * EXCEPT (fetch_ts, ingest_ts) FROM telemetry_raw.alerts
            WHERE alert_start_ts BETWEEN start_ts AND end_ts
            QUALIFY (
                ROW_NUMBER() OVER (
                    PARTITION BY data_provider, site_id, device_id, alert_id, alert_start_ts
                )
            ) = 1
        );
        """
    )


def _process_telemetry_alerts(environment: PlatformEnvironment) -> None:
    _setup_platform_alerts(environment)
    _merge_telemetry_alerts_into_platform_alerts(environment)
    _push_platform_alerts(environment)


def _setup_platform_alerts(environment: PlatformEnvironment) -> None:
    bigquery.engine.execute_query(
        f"""
        CREATE TABLE IF NOT EXISTS platform_{environment}.alerts (
            device_id INTEGER NOT NULL,
            external_id STRING NOT NULL,
            type STRING NOT NULL,
            severity STRING NOT NULL,
            error_message STRING NOT NULL,
            is_resolved BOOLEAN NOT NULL,
            alert_start TIMESTAMP NOT NULL,
            push_ts TIMESTAMP
        )
        PARTITION BY TIMESTAMP_TRUNC(push_ts, DAY)
        CLUSTER BY device_id, external_id;
        """
    )


def _merge_telemetry_alerts_into_platform_alerts(environment: PlatformEnvironment) -> None:
    bigquery.engine.execute_query(
        f"""
        MERGE INTO platform_{environment}.alerts AS pa
        USING (
            SELECT
                internal.device_id AS device_id,
                alert_id AS external_id,
                alert_type AS type,
                IF(
                    alert_severity IN ('Informational', 'Warning', 'Critical'),
                    alert_severity,
                    'Informational'
                ) AS severity,
                alert_message AS error_message,
                alert_is_resolved AS is_resolved,
                alert_start_ts AS alert_start,
                TIMESTAMP(NULL) AS push_ts
            FROM telemetry_rfn.alerts(
                (
                    TIMESTAMP(CURRENT_DATE() - (INTERVAL {MAX_HISTORY_DEPTH_YEARS} YEAR))
                    + (CURRENT_TIMESTAMP() - TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), DAY))
                ),
                CURRENT_TIMESTAMP()
            )
            JOIN telemetry_rfn.id_map
            ON external.data_provider = data_provider
            AND external.site_id = site_id
            AND external.device_id = device_id
            AND internal.environment = '{environment}'
        ) AS ta
        ON pa.device_id = ta.device_id AND pa.external_id = ta.external_id
        WHEN NOT MATCHED BY TARGET THEN INSERT ROW;
        """
    )


def _push_platform_alerts(environment: PlatformEnvironment) -> None:
    alerts = bigquery.engine.execute_query(
        f"SELECT * EXCEPT (push_ts) FROM platform_{environment}.alerts WHERE push_ts IS NULL;"
    )

    api_url = f"{PLATFORM_API_URLS[environment]}/api/internal/alerts"

    api_key = secret_manager.access_secret(PROJECT_ID, PLATFORM_API_KEY_SECRET_NAME.format(environment=environment))

    for alert in alerts:
        sub_logger = logger.bind(environment=environment, api_url=api_url, alert=alert)

        sub_logger.info("Pushing alert to internal API")

        with Timer() as timer:
            response = _push_alert_request(api_url, api_key, alert)

        status_code = response.status_code
        reason_phrase = HTTPStatus(status_code).phrase

        duration = timer.elapsed_ms / 1_000

        sub_logger.info(
            "Pushed alert to internal API",
            status_code=status_code,
            reason_phrase=reason_phrase,
            duration=duration,
        )

    bigquery.engine.execute_query(
        f"UPDATE platform_{environment}.alerts SET push_ts = CURRENT_TIMESTAMP() WHERE push_ts IS NULL;"
    )


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _push_alert_request(api_url: str, api_key: str, alert: dict[str, Any]) -> requests.Response:
    response = request.post(
        api_url,
        params={"api_key": api_key},
        data=orjson.dumps(alert),
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.CREATED, HTTPStatus.CONFLICT, HTTPStatus.NOT_FOUND})
