import pytest

from tests.unit import samples


@pytest.fixture(scope="function")
def gcs_signed_url_generation(mocker):
    """Applicable only for the O&M site level tasks"""
    mocker.patch("app.helpers.files.file_handler.service_account")
    mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
    mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = (
        samples.TEST_GCP_LINK
    )

    yield
