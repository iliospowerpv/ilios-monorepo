import functions_framework
import orjson
from flask import Request, Response
from pydantic import ValidationError

from . import service
from .common import cloud_logging, response
from .common.params import VerifyTokenServiceRequestParams

logger = cloud_logging.get_logger(__name__)


@functions_framework.http
def verify_token_service(request: Request) -> Response:
    cloud_logging.setup()

    if request.method != "POST":
        return response.method_not_allowed()

    params = VerifyTokenServiceRequestParams.from_request(request)

    params_data = params.model_dump(exclude={"token"})

    logger.info("Verifying token to external API", params=params_data)

    return response.ok() if service.verify_token(params) else response.unauthorized()


@functions_framework.errorhandler(ValidationError)
def handle_validation_error(error: ValidationError) -> Response:
    errors_json_pretty = orjson.dumps(error.errors(), option=orjson.OPT_INDENT_2).decode("utf-8")
    logger.error("Failed to validate service request:\n%s", errors_json_pretty)
    return response.bad_request()


@functions_framework.errorhandler(Exception)
def handle_unexpected_error(error: Exception) -> Response:
    logger.exception("Failed to complete service request: %r", error)
    return response.internal_server_error()
