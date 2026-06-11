# ─────────────────────────────────────────────────────────────────────────────
# ⚠️ LEGACY / DECOMMISSIONING — DO NOT EXTEND.
# Part of the external GCP telemetry ingestion pipeline (BigQuery + Firestore),
# SUPERSEDED by in-process Native Telemetry Ingestion V2 in backend/ilios-server
# (PostgreSQL). No longer the source of truth for app-facing telemetry; app-facing
# consumers are gated OFF by default behind `legacy_telemetry_enabled`. Do not add
# new callers or re-point V2 code here. See ../../../README.md for the decommission
# plan. Hard deletion is a separate, later sprint.
# ─────────────────────────────────────────────────────────────────────────────
import functions_framework
from flask import Request, Response

from . import job
from .common import cloud_logging, firestore, pubsub, response
from .common.constants import FETCH_TELEMETRY_DATA_TOPIC_ID, TELEMETRY_CONFIG_COLLECTION_ID
from .common.enums import PlatformEnvironment

logger = cloud_logging.get_logger(__name__)


@functions_framework.http
def request_telemetry_data_job(request: Request) -> Response:
    cloud_logging.setup()

    if request.method != "POST":
        return response.method_not_allowed()

    topic_id = FETCH_TELEMETRY_DATA_TOPIC_ID

    counts = {}

    for environment in PlatformEnvironment.as_list():
        collection_id = TELEMETRY_CONFIG_COLLECTION_ID.format(environment=environment)

        sub_logger = logger.bind(environment=environment, collection_id=collection_id)

        counts[environment] = 0

        for document in firestore.database.stream_documents(collection_id):
            sub_logger.info("Parsing config from Firestore", document_id=document.id)

            for payload in job.parse_telemetry_config(environment, document.data):
                pubsub.publisher.publish(topic_id, payload)
                counts[environment] += 1

    pubsub.publisher.wait_until_published()

    logger.info("Published messages to Pub/Sub", topic_id=topic_id, counts=counts)

    return response.ok()


@functions_framework.errorhandler(Exception)
def handle_unexpected_error(error: Exception) -> Response:
    logger.exception("Failed to complete job request: %r", error)
    return response.internal_server_error()
