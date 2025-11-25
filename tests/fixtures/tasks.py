import copy

import pytest

from app.crud.task import TaskCRUD
from tests.unit import samples


@pytest.fixture(scope="function")
def site_task(db_session, site_default_board, non_system_user_id):
    """Create a site-level Asset task where assignee and creator is non system user"""
    task_crud = TaskCRUD(db_session)
    task_payload = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
    task_payload.update(
        {
            "status_id": site_default_board.get_statuses_ids()[0],
            "creator_id": non_system_user_id,
            "assignee_id": non_system_user_id,
            "board_id": site_default_board.id,
        }
    )

    task = task_crud.create_item(task_payload)

    yield task

    task_crud.delete_by_id(task.id)


@pytest.fixture(scope="function")
def site_task_id(site_task):
    yield site_task.id


@pytest.fixture(scope="function")
def company_task(db_session, company_default_board, non_system_user_id):
    """Create a company level Asset task where assignee and creator is non system user"""
    task_crud = TaskCRUD(db_session)
    task_payload = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
    task_payload.update(
        {
            "status_id": company_default_board.get_statuses_ids()[0],
            "creator_id": non_system_user_id,
            "assignee_id": non_system_user_id,
            "board_id": company_default_board.id,
            "external_id": "CMP-1",
        }
    )

    task = task_crud.create_item(task_payload)

    yield task

    task_crud.delete_by_id(task.id)


@pytest.fixture(scope="function")
def site_lease_document_task(db_session, site_lease_document_default_board, non_system_user_id):
    """Create a document level Diligence task where assignee and creator is non system user"""
    task_crud = TaskCRUD(db_session)
    task_payload = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
    task_payload.update(
        {
            "status_id": site_lease_document_default_board.get_statuses_ids()[0],
            "creator_id": non_system_user_id,
            "assignee_id": non_system_user_id,
            "board_id": site_lease_document_default_board.id,
            "external_id": "SLD-1",
        }
    )

    task = task_crud.create_item(task_payload)

    yield task

    task_crud.delete_by_id(task.id)


@pytest.fixture(scope="function")
def site_om_task(db_session, site_om_default_board, non_system_user_id):
    """Create a site-level O&M task where assignee and creator is non system user"""
    task_crud = TaskCRUD(db_session)
    task_payload = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
    task_payload.update(
        {
            "status_id": site_om_default_board.get_statuses_ids()[0],
            "creator_id": non_system_user_id,
            "assignee_id": non_system_user_id,
            "board_id": site_om_default_board.id,
            "external_id": "OM-1",
        }
    )

    task = task_crud.create_item(task_payload)

    yield task

    task_crud.delete_by_id(task.id)


@pytest.fixture(scope="function")
def company_om_task(db_session, company_om_default_board, non_system_user_id):
    """Create a company-level O&M task where assignee and creator is non system user"""
    task_crud = TaskCRUD(db_session)
    task_payload = copy.deepcopy(samples.TEST_TASK_PAYLOAD)
    task_payload.update(
        {
            "status_id": company_om_default_board.get_statuses_ids()[0],
            "creator_id": non_system_user_id,
            "assignee_id": non_system_user_id,
            "board_id": company_om_default_board.id,
            "external_id": "Company-OM-1",
        }
    )

    task = task_crud.create_item(task_payload)

    yield task

    task_crud.delete_by_id(task.id)
