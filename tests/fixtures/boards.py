import pytest

from app.crud.board import BoardCRUD
from app.helpers.task_tracker.board_defaults_helper import create_default_board, create_default_document_tasks
from app.models.board import BoardModuleEnum, BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum


@pytest.fixture(scope="function")
def site_default_board(db_session, site):
    board = create_default_board(site.id, BoardRelatedEntityTypeEnum.site, db_session)

    yield board


@pytest.fixture(scope="function")
def site_default_board_id(site_default_board):
    yield site_default_board.id


@pytest.fixture(scope="function")
def company_default_board(db_session, company):
    create_default_board(company.id, BoardRelatedEntityTypeEnum.company, db_session)

    yield company.related_boards[0].board


@pytest.fixture(scope="function")
def company_default_board_id(company_default_board):
    yield company_default_board.id


@pytest.fixture(scope="function")
def site_lease_document_default_board(db_session, site_lease_document, system_user_id):
    default_board = create_default_board(
        site_lease_document.site_id,
        BoardRelatedEntityTypeEnum.site,
        db_session,
        BoardRelatedEntityTypeExtraEnum.document,
    )
    create_default_document_tasks(db_session, default_board, [site_lease_document], system_user_id)

    yield site_lease_document.task.board

    BoardCRUD(db_session).delete_by_id(default_board.id)


@pytest.fixture(scope="function")
def site_om_default_board(db_session, site):
    board = create_default_board(site.id, BoardRelatedEntityTypeEnum.site, db_session, module=BoardModuleEnum.om)

    yield board


@pytest.fixture(scope="function")
def company_om_default_board(db_session, company):
    board = create_default_board(company.id, BoardRelatedEntityTypeEnum.company, db_session, module=BoardModuleEnum.om)

    yield board
