import pytest

from app.crud.das_connection import DASConnectionCRUD
from app.firestore_models.firestore_company_config import FSCompanyConfig, FSConnection, FSSite
from app.models.telemetry import DASProvidersEnum
from tests.unit import samples


@pytest.fixture(scope="function", params=[DASProvidersEnum.kmc])
def das_connection(db_session, company_id, request):
    """By default, returns KMC das connection"""
    provider = request.param
    das_connection_record = {
        "company_id": company_id,
        "name": samples.TEST_KMC_DAS_CONNECTION_PAYLOAD["name"],
        "provider": provider,
        "secret_token_name": "test_token",
    }
    connection_crud = DASConnectionCRUD(db_session)
    test_connection = connection_crud.create_item(das_connection_record)
    test_connection_id = test_connection.id

    yield test_connection

    connection_crud.delete_by_id(test_connection_id)


@pytest.fixture(scope="function")
def fs_company_config(das_connection):
    fs_connection = FSConnection(
        _id=das_connection.id,
        data_provider=das_connection.provider.name,
        token_secret_id=das_connection.secret_token_name,
    )
    fs_company_config = FSCompanyConfig(_id=das_connection.company_id, connections=[fs_connection])

    yield fs_company_config


@pytest.fixture(scope="function")
def fs_company_config_with_site(fs_company_config, das_connection, site_id):
    fs_site = FSSite(_id=site_id, connection_id=das_connection.id, external_id="123asdsad")
    fs_company_config.sites.append(fs_site)

    yield fs_company_config
