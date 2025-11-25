from http import HTTPStatus
from typing import Any

import orjson
from flask import Response


def response(
    status_code: int,
    payload: Any,
    headers: dict[str, str] | None = None,
) -> Response:
    assert status_code in range(100, 600)
    default_headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }
    return Response(
        response=orjson.dumps(payload),
        status=status_code,
        headers=(default_headers | (headers or {})),
    )


def success(result: Any) -> Response:
    return response(HTTPStatus.OK, result)


def ok(message: str | None = None) -> Response:
    return response(HTTPStatus.OK, {"message": message or HTTPStatus.OK.phrase})


def bad_request(message: str | None = None) -> Response:
    return response(HTTPStatus.BAD_REQUEST, {"message": message or HTTPStatus.BAD_REQUEST.phrase})


def unauthorized(message: str | None = None) -> Response:
    return response(HTTPStatus.UNAUTHORIZED, {"message": message or HTTPStatus.UNAUTHORIZED.phrase})


def not_found(message: str | None = None) -> Response:
    return response(HTTPStatus.NOT_FOUND, {"message": message or HTTPStatus.NOT_FOUND.phrase})


def method_not_allowed(message: str | None = None) -> Response:
    return response(HTTPStatus.METHOD_NOT_ALLOWED, {"message": message or HTTPStatus.METHOD_NOT_ALLOWED.phrase})


def internal_server_error(message: str | None = None) -> Response:
    return response(HTTPStatus.INTERNAL_SERVER_ERROR, {"message": message or HTTPStatus.INTERNAL_SERVER_ERROR.phrase})


def acknowledge(response: Response) -> Response:
    response.status = HTTPStatus.OK
    return response
