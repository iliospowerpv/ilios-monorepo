from http import HTTPStatus

import orjson
import requests

from ...common import request
from ...common.constants import DATA_PROVIDER_API_URLS, MAX_RETRIES_PER_REQUEST, TIMEOUT_PER_REQUEST
from ...common.entities import Site
from ...common.enums import DataProvider
from ...common.exceptions import TokenUnauthorizedError
from ...common.retrying import retry_on_exception
from ...common.validation import validate_response_status

API_URL = DATA_PROVIDER_API_URLS[DataProvider.KMC]


def retrieve_sites(token: str) -> list[Site]:
    response = _get_licenses_request(token)

    if response.status_code == HTTPStatus.UNAUTHORIZED:
        raise TokenUnauthorizedError("Token Unauthorized")

    payload = orjson.loads(response.content)

    return sorted(
        (
            Site(
                id=site_item["id"],
                name=site_item["name"],
            )
            for site_item in payload["data"]
        ),
        key=lambda site: site["name"],
    )


@retry_on_exception(requests.RequestException, max_retries=MAX_RETRIES_PER_REQUEST)
def _get_licenses_request(token: str) -> requests.Response:
    response = request.get(
        f"{API_URL}/v2/api/auth/me/activelicenses",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT_PER_REQUEST,
    )
    return validate_response_status(response, expect={HTTPStatus.UNAUTHORIZED})
