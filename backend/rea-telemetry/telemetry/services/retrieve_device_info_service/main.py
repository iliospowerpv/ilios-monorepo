import functions_framework
import orjson
from flask import Request, Response
from pydantic import ValidationError

from . import service
from .common import cloud_logging, response
from .common.exceptions import DeviceNotFoundError, SiteNotFoundError, TokenUnauthorizedError
from .common.params import RetrieveDeviceInfoServiceRequestParams

logger = cloud_logging.get_logger(__name__)


@functions_framework.http
def retrieve_device_info_service(request: Request) -> Response:
    cloud_logging.setup()

    if request.method != "POST":
        return response.method_not_allowed()

    params = RetrieveDeviceInfoServiceRequestParams.from_request(request)

    params_data = params.model_dump()

    logger.info("Retrieving device info from external API", params=params_data)

    return response.success(service.retrieve_device_info(params))


@functions_framework.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError) -> Response:
    errors_json_pretty = orjson.dumps(error.errors(), option=orjson.OPT_INDENT_2).decode("utf-8")
    logger.error("Failed to validate service request:\n%s", errors_json_pretty)
    return response.bad_request()


@functions_framework.errorhandler(TokenUnauthorizedError)
def handle_token_unauthorized_error(error: TokenUnauthorizedError) -> Response:
    return response.unauthorized(str(error))


@functions_framework.errorhandler(SiteNotFoundError)
def handle_site_not_found_error(error: SiteNotFoundError) -> Response:
    return response.not_found(str(error))


@functions_framework.errorhandler(DeviceNotFoundError)
def handle_device_not_found_error(error: DeviceNotFoundError) -> Response:
    return response.not_found(str(error))


@functions_framework.errorhandler(Exception)
def handle_unexpected_error(error: Exception) -> Response:
    logger.exception("Failed to complete service request: %r", error)
    return response.internal_server_error()
