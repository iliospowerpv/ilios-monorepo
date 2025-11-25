import pickle
from copy import deepcopy

import pytest

from app.crud.telemetry_mapping import TelemetryDeviceMappingCRUD, TelemetrySiteMappingCRUD
from tests.unit import samples


@pytest.fixture(scope="function")
def telemetry_site_mapping(db_session, site_id, das_connection):
    mapping_record = {
        "site_id": site_id,
        "connection_id": das_connection.id,
        "telemetry_site_id": "123",
        "telemetry_site_name": "test mapping",
    }
    site_mapping_crud = TelemetrySiteMappingCRUD(db_session)
    test_mapping = site_mapping_crud.create_item(mapping_record)
    test_mapping_id = test_mapping.id

    yield test_mapping

    site_mapping_crud.delete_by_id(test_mapping_id)


@pytest.fixture(scope="function")
def telemetry_device_mapping(db_session, device_id, telemetry_site_mapping):
    mapping_record = {
        "device_id": device_id,
        "telemetry_device_id": "123",
        "telemetry_device_name": "test device mapping",
    }
    device_mapping_crud = TelemetryDeviceMappingCRUD(db_session)
    test_mapping = device_mapping_crud.create_item(mapping_record)
    test_mapping_id = test_mapping.id

    yield test_mapping

    device_mapping_crud.delete_by_id(test_mapping_id)


@pytest.fixture(scope="function")
def mocked_big_query_site_data(mocker):
    cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
    cache_mock.return_value.get.return_value = None
    telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
    telemetry_bq_engine.return_value.execute_query.return_value = samples.SITE_DASHBOARD_BIGQUERY_RESPONSE


@pytest.fixture(scope="function")
def mocked_big_query_site_actual_production_data(mocker, site_id):
    cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
    cache_mock.return_value.get.return_value = None
    telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
    site_response = deepcopy(samples.SITE_DASHBOARD_BIGQUERY_RESPONSE)
    site_response[0].update({"site_id": site_id})
    telemetry_bq_engine.return_value.execute_query.side_effect = [
        site_response,
        samples.SITE_TODAY_CUMULATIVE_BQ_RESPONSE,
    ]


@pytest.fixture(scope="function")
def mocked_big_query_site_actual_production_data_from_cache(mocker, site_id):
    cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
    cache_mock.return_value.get.side_effect = [
        pickle.dumps({site_id: (42.00, 13.000)}),
        pickle.dumps(samples.SITE_TODAY_CUMULATIVE_CACHED_RESPONSE),
    ]
    mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")


@pytest.fixture(scope="function")
def mocked_big_query_company_site(mocker, company_id, site_id):
    bq_response = deepcopy(samples.SITE_DASHBOARD_BIGQUERY_RESPONSE)
    bq_response[0].update({"site_id": site_id, "company_id": company_id})
    cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
    cache_mock.return_value.get.return_value = None
    telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
    telemetry_bq_engine.return_value.execute_query.return_value = bq_response
