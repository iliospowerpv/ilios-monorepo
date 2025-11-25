from http import HTTPStatus

import requests


def validate_response_status(response: requests.Response, expect: set[HTTPStatus] | None = None) -> requests.Response:
    expect_with_ok = (expect or set()) | {HTTPStatus.OK}

    if (status_code := response.status_code) not in expect_with_ok:
        reason_phrase = HTTPStatus(status_code).phrase

        message = f"{status_code} {reason_phrase}: {response.request.method} {response.request.url}: {response.text}"

        raise requests.HTTPError(message, response=response)

    return response
