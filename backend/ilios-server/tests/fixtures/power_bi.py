import pickle

import pytest

import tests.unit.samples as samples
from app.static import PBI_CONTENT_TYPE_HEADER
from tests.utils import create_file_response, create_response


@pytest.fixture(scope="function")
def pbi_token_reports_mock_200(mocker):
    """Mock APIs for token getting and reports list retrieval"""
    requests_mock = mocker.patch("app.helpers.powerbi.requests")
    requests_mock.request.side_effect = [
        create_response(200, samples.POWER_BI_ACCESS_TOKEN_RESPONSE),
        create_response(200, samples.POWER_BI_REPORTS_RESPONSE),
    ]

    yield


@pytest.fixture(scope="function")
def pbi_reports_mock_200(mocker):
    requests_mock = mocker.patch("app.helpers.powerbi.requests")
    requests_mock.request.return_value = create_response(200, samples.POWER_BI_REPORTS_RESPONSE)

    yield


@pytest.fixture(scope="function")
def pbi_token_mock_400(mocker):
    requests_mock = mocker.patch("app.helpers.powerbi.requests")
    requests_mock.request.return_value = create_response(400, {})
    yield


@pytest.fixture(scope="function")
def pbi_no_cache(mocker):
    cache_mock = mocker.patch("app.helpers.powerbi.get_cache")
    cache_mock.return_value.get.return_value = None
    yield


@pytest.fixture(scope="function")
def pbi_with_cache(mocker):
    cache_mock = mocker.patch("app.helpers.powerbi.get_cache")
    cache_mock.return_value.get.return_value = pickle.dumps(samples.PBI_CACHE_VALUE)
    yield


@pytest.fixture(scope="function")
def pbi_token_embed_mock_200(mocker):
    """Mock APIs for token getting and embedding token generation"""
    requests_mock = mocker.patch("app.helpers.powerbi.requests")
    requests_mock.request.side_effect = [
        create_response(200, samples.POWER_BI_ACCESS_TOKEN_RESPONSE),
        create_response(200, samples.POWER_BI_EMBED_TOKEN_RESPONSE),
    ]

    yield


@pytest.fixture(scope="function")
def pbi_generic_json_mock_200(mocker):
    """Mock APIs for token getting and any generic response"""
    requests_mock = mocker.patch("app.helpers.powerbi.requests")
    requests_mock.request.return_value = create_response(200, samples.POWER_BI_GENERIC_RESPONSE)

    yield requests_mock


@pytest.fixture(scope="function")
def pbi_response_pdf_mock_200(mocker):
    """Mock APIs for token getting and any generic response"""
    requests_mock = mocker.patch("app.helpers.powerbi.requests")
    requests_mock.request.return_value = create_file_response(
        200, b"", headers={PBI_CONTENT_TYPE_HEADER: "application/pdf"}
    )

    yield
