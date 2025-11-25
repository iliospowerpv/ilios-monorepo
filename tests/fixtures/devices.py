import pytest

from app.crud.device import DeviceCRUD
from tests.unit import samples


@pytest.fixture(scope="function", params=[samples.TEST_INVERTER_DEVICE_BODY])
def device(db_session, site_id, request):
    payload = request.param
    payload["site_id"] = site_id
    device_crud = DeviceCRUD(db_session)
    test_device = device_crud.create_item(payload)

    yield test_device

    device_crud.delete_by_id(test_device.id)


@pytest.fixture(scope="function")
def device_id(device):

    yield device.id
