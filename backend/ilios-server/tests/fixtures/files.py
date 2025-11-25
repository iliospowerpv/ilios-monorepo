import pytest

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.crud.file import FileCRUD
from tests.unit import samples


@pytest.fixture(scope="function")
def file(db_session, non_system_user_id, document):
    test_file_name = samples.TEST_FILE_NAME
    filepath = f"test/file/path/{test_file_name}"
    file_metadata = {
        "filepath": filepath,
        "filename": test_file_name,
        "user_id": non_system_user_id,
        "document_id": document.id,
    }
    file_crud = FileCRUD(db_session)
    file = file_crud.create_item(file_metadata)
    # use pre saved file_id in case file was already removed by test
    file_id = file.id

    yield file

    file_crud.delete_by_id(file_id)


@pytest.fixture(scope="function")
def ai_result(db_session, file):
    record_metadata = {"file_id": file.id, "status": "processing"}
    ai_results_crud = AIParsingResultCRUD(db_session)
    ai_result = ai_results_crud.create_item(record_metadata)
    # use pre saved record_id in case it was already removed by test
    record_id = ai_result.id

    yield ai_result

    ai_results_crud.delete_by_id(record_id)
