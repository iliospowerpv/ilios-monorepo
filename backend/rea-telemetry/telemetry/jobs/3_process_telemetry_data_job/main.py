import functions_framework
from flask import Request, Response

from . import job
from .common import cloud_logging, response
from .common.enums import TelemetryCategory
from .common.timer import Timer

logger = cloud_logging.get_logger(__name__)

PROCESS_TELEMETRY_DATA_JOBS = {
    TelemetryCategory.POINTS: job.process_telemetry_points,
    TelemetryCategory.ALERTS: job.process_telemetry_alerts,
}


@functions_framework.http
def process_telemetry_data_job(request: Request) -> Response:
    cloud_logging.setup()

    if request.method != "POST":
        return response.method_not_allowed()

    logger.info("Preparing ID map in BigQuery")

    with Timer() as timer:
        job.prepare_id_map()

    duration = timer.elapsed_ms / 1_000

    logger.info("Prepared ID map in BigQuery", duration=duration)

    for category, process_telemetry_data_job in PROCESS_TELEMETRY_DATA_JOBS.items():
        sub_logger = logger.bind(category=category)

        sub_logger.info("Processing %s in BigQuery", category)

        with Timer() as timer:
            process_telemetry_data_job()

        duration = timer.elapsed_ms / 1_000

        sub_logger.info("Processed %s in BigQuery", category, duration=duration)

    return response.ok()


@functions_framework.errorhandler(Exception)
def handle_unexpected_error(error: Exception) -> Response:
    logger.exception("Failed to complete job request: %r", error)
    return response.internal_server_error()
