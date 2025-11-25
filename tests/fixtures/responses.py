import pytest
from requests import Response


@pytest.fixture(scope="class")
def response_200():
    response = Response()
    response.status_code = 200
    response._content = b"{}"
    return response


@pytest.fixture(scope="class")
def response_400():
    response = Response()
    response.status_code = 400
    response._content = b"{}"
    response.reason = "Bad request custom reason"
    return response
