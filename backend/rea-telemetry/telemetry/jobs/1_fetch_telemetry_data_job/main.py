import functions_framework
import orjson
from flask import Request, Response
from pydantic import ValidationError

from . import job
from .common import cloud_logging, pubsub, response
from .common.constants import INGEST_TELEMETRY_DATA_TOPIC_ID
from .common.enums import TelemetryCategory
from .common.exceptions import DataUnavailableError, DeviceNotFoundError, SiteNotFoundError, TokenUnauthorizedError
from .common.params import FetchTelemetryDataJobRequestParams, PlatformParams
from .common.thread_local import ThreadLocal
from .common.timer import Timer

logger = cloud_logging.get_logger(__name__)

thread_local = ThreadLocal()

FETCH_TELEMETRY_DATA_JOBS = {
    TelemetryCategory.POINTS: job.fetch_telemetry_points,
    TelemetryCategory.ALERTS: job.fetch_telemetry_alerts,
}


@functions_framework.http
def fetch_telemetry_data_job(request: Request) -> Response:
    cloud_logging.setup()

    if request.method != "POST":
        return response.method_not_allowed()

    params = FetchTelemetryDataJobRequestParams.from_request(request)

    thread_local.platform_params = params.platform

    params_data = params.model_dump()

    topic_id = INGEST_TELEMETRY_DATA_TOPIC_ID

    counts = {}

    for category, fetch_telemetry_data_job in FETCH_TELEMETRY_DATA_JOBS.items():
        sub_logger = logger.bind(category=category, params=params_data)

        sub_logger.info("Fetching %s from external API", category)

        counts[category] = 0

        with Timer() as timer:
            for payload in fetch_telemetry_data_job(params):
                pubsub.publisher.publish(topic_id, payload, category=category)
                counts[category] += 1

        count = counts[category]

        duration = timer.elapsed_ms / 1_000

        sub_logger.info("Fetched %s from external API", category, count=count, duration=duration)

    pubsub.publisher.wait_until_published()

    logger.info("Published messages to Pub/Sub", topic_id=topic_id, counts=counts)

    return response.ok()


@functions_framework.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError) -> Response:
    errors_json_pretty = orjson.dumps(error.errors(), option=orjson.OPT_INDENT_2).decode("utf-8")
    logger.error("Failed to validate job request:\n%s", errors_json_pretty)
    return response.bad_request()


@functions_framework.errorhandler(TokenUnauthorizedError)
def handle_token_unauthorized_error(error: TokenUnauthorizedError) -> Response:
    return response.acknowledge(response.unauthorized(str(error)))


@functions_framework.errorhandler(SiteNotFoundError)
def handle_site_not_found_error(error: SiteNotFoundError) -> Response:
    from .job import platform

    params: PlatformParams = thread_local.platform_params

    platform.delete_device(params)

    return response.acknowledge(response.not_found(str(error)))


@functions_framework.errorhandler(DeviceNotFoundError)
def handle_device_not_found_error(error: DeviceNotFoundError) -> Response:
    from .job import platform

    params: PlatformParams = thread_local.platform_params

    platform.delete_device(params)

    return response.acknowledge(response.not_found(str(error)))


@functions_framework.errorhandler(DataUnavailableError)
def handle_data_unavailable_error(error: DataUnavailableError) -> Response:
    return response.ok(str(error))


@functions_framework.errorhandler(Exception)
def handle_unexpected_error(error: Exception) -> Response:
    logger.exception("Failed to complete job request: %r", error)
    return response.internal_server_error()
