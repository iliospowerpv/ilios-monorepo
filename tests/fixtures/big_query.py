import pytest


@pytest.fixture(scope="function")
def ignore_bq_sync(mocker):
    """General mock to ignore BQ Sync helpers"""
    mocker.patch("app.helpers.bq_data_sync_helper.CharacteristicsHandler.sync_to_bq", return_value=True)


@pytest.fixture(scope="function")
def bq_client_mock(mocker):
    """Mock BQ client to track all raw calls"""
    mocker.patch("app.bigquery.bigquery.service_account.Credentials.from_service_account_file")
    bq_client_mock = mocker.patch("app.bigquery.bigquery.bigquery.Client", autospec=True)

    yield bq_client_mock

    bq_client_mock().reset_mock()
