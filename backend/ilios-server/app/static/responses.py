from http import HTTPStatus

from fastapi import status

HTTP_404_DETAILS = {
    "description": "Response about not found resource",
    "content": {
        "application/json": {"example": [{"code": status.HTTP_404_NOT_FOUND, "message": HTTPStatus.NOT_FOUND.phrase}]}
    },
}

HTTP_403_DETAILS = {
    "description": "Response about not forbidden resource",
    "content": {
        "application/json": {"example": [{"code": status.HTTP_403_FORBIDDEN, "message": HTTPStatus.FORBIDDEN.phrase}]}
    },
}

HTTP_422_DETAILS = {
    "description": "Default 422 response",
    "content": {
        "application/json": {
            "example": {"code": status.HTTP_422_UNPROCESSABLE_ENTITY, "message": HTTPStatus.UNPROCESSABLE_ENTITY.phrase}
        }
    },
}

HTTP_404_RESPONSE = {status.HTTP_404_NOT_FOUND: HTTP_404_DETAILS}

HTTP_403_RESPONSE = {status.HTTP_403_FORBIDDEN: HTTP_403_DETAILS}

HTTP_422_RESPONSE = {status.HTTP_422_UNPROCESSABLE_ENTITY: HTTP_422_DETAILS}


def HTTP_409_RESPONSE(message: str = HTTPStatus.CONFLICT.phrase) -> dict:  # noqa: N802
    http_409_details = {
        "description": "Response about conflicting existing resource",
        "content": {
            "application/json": {
                "example": [
                    {
                        "code": status.HTTP_409_CONFLICT,
                        "message": message,
                    }
                ]
            }
        },
    }
    return {status.HTTP_409_CONFLICT: http_409_details}


def HTTP_400_RESPONSE(message: str = HTTPStatus.BAD_REQUEST.phrase) -> dict:  # noqa: N802
    http_400_details = {
        "description": "Response about bad request",
        "content": {
            "application/json": {
                "example": [
                    {
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": message,
                    }
                ]
            }
        },
    }
    return {status.HTTP_400_BAD_REQUEST: http_400_details}


def HTTP_410_RESPONSE(message: str = HTTPStatus.GONE.phrase) -> dict:  # noqa: N802
    http_410_details = {
        "description": "Response about request gone",
        "content": {"application/json": {"example": [{"code": status.HTTP_410_GONE, "message": message}]}},
    }
    return {status.HTTP_410_GONE: http_410_details}
