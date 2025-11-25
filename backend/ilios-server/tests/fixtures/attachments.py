import pytest

from app.crud.attachment import AttachmentCRUD
from tests.unit import samples


@pytest.fixture(scope="function")
def attachment(db_session, non_system_user_id, site_task_id):
    test_attachment_name = samples.TEST_ATTACHMENT_NAME
    filepath = f"test/attachment/path/{test_attachment_name}"
    file_metadata = {
        "filepath": filepath,
        "filename": test_attachment_name,
        "user_id": non_system_user_id,
        "task_id": site_task_id,
    }
    attachment_crud = AttachmentCRUD(db_session)
    attachment = attachment_crud.create_item(file_metadata)
    # use pre saved attachment_id in case file was already removed by test
    attachment_id = attachment.id

    yield attachment

    attachment_crud.delete_by_id(attachment_id)


@pytest.fixture(scope="function")
def attachment_id(attachment):
    yield attachment.id
