import pytest

from app.crud.device_document import DeviceDocumentCRUD
from tests.unit import samples


@pytest.fixture(scope="function")
def device_document(db_session, device_id):
    document_name = samples.TEST_DEVICE_DOCUMENT_NAME
    filepath = f"test/documents/path/{document_name}"
    document_metadata = {
        "filepath": filepath,
        "filename": document_name,
        "device_id": device_id,
        "category": "warranty",
    }
    document_crud = DeviceDocumentCRUD(db_session)
    document = document_crud.create_item(document_metadata)
    document_id = document.id

    yield document

    document_crud.delete_by_id(document_id)


@pytest.fixture(scope="function")
def device_document_id(device_document):
    yield device_document.id
