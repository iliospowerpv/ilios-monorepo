from starlette import status


def test_health_check(client):
    """Sample pytest test function with the pytest fixture as an argument."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK


def test_404(client):
    """Sample pytest test function with the pytest fixture as an argument."""
    response = client.get("/not_exists")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_docs(client):
    """Validate docs server"""
    response = client.get("/docs")
    assert response.status_code == status.HTTP_200_OK


def test_openapi(client):
    """Validate openapi.json is generated"""
    response = client.get("/openapi.json")
    assert response.status_code == status.HTTP_200_OK
