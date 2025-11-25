import logging
from datetime import datetime
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.board import BoardCRUD
from app.crud.board_related_entity import BoardRelatedEntityCRUD
from app.crud.board_status import BoardStatusCRUD
from app.crud.task import TaskCRUD
from app.helpers.task_tracker import TaskTrackerHandlerFactory
from app.models.board import Board, BoardModuleEnum, BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.models.document import Document
from app.static import DocumentBoardDefaultStatuses

logger = logging.getLogger(__name__)


def create_default_board(
    entity_id: int,
    entity_type: BoardRelatedEntityTypeEnum,
    db_session: Session,
    extra_entity_type: BoardRelatedEntityTypeExtraEnum = None,
    # most boards are Asset, have it as default:
    # there is no sense of making the 'module' field mandatory
    # since there are a lot of occurrences of the method through the codebase
    module: BoardModuleEnum = BoardModuleEnum.asset,
):
    """Create default board for the specific entity"""
    if extra_entity_type:
        description = (f"Default board for {entity_type.value} #{entity_id} documents",)
        module = BoardModuleEnum.diligence
    else:
        description = f"Default {module.value} board for {entity_type.value} #{entity_id}"
    # create new board
    board = BoardCRUD(db_session).create_item(
        {"description": description, "name": "Default board", "module": module.value}
    )
    board_id = board.id
    logger.info(f"Created board for {entity_type.value} with id={entity_id}, board id={board_id}")

    # attach board to the related entity
    related_entity_data = {"entity_id": entity_id, "entity_type": entity_type, "board_id": board_id}
    if extra_entity_type:
        related_entity_data["extra_entity_type"] = extra_entity_type
    BoardRelatedEntityCRUD(db_session).create_item(related_entity_data)
    logger.info(
        f"Created {entity_type.value} <-> board relationship, {entity_type.value} id={entity_id}, board id={board_id}"
    )

    # populate board statuses
    handler = TaskTrackerHandlerFactory(db_session).get_instance(board)
    board_default_statuses = handler.get_default_statuses()
    BoardStatusCRUD(db_session).create_items(board_default_statuses)
    logger.info(
        f"Created {len(board_default_statuses)} default statuses for {entity_type.value} board with id={board_id}"
    )

    return board


def create_default_document_tasks(
    db_session: Session, board: Board, documents: List[Document], creator_id: int, freeze_external_id=False
):
    """
    Additional param freeze_external_id allow do not call DB everytime, but use the same start index.
    Might lead to the UniqueConstraintDuplicationError, but should be OK for DB migration
    """
    # available only for the Document board
    if board.related_entity.extra_entity_type != BoardRelatedEntityTypeExtraEnum.document:
        logger.warning(
            f"Default task creation is not applicable for the '{board.related_entity.entity_type}' boards ({board.id=})"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The '{board.related_entity.entity_type}.value' boards are not supported for default tasks adding",
        )
    max_prefix_counter = 0
    default_document_tasks = []
    handler = TaskTrackerHandlerFactory(db_session).get_instance(board)
    task_crud = TaskCRUD(db_session)
    # get default status name to be set
    expected_status = DocumentBoardDefaultStatuses.to_upload.value
    default_status = [board_status for board_status in board.statuses if board_status.name == expected_status][0]
    start_external_id = None
    if freeze_external_id:
        start_external_id = handler.get_task_max_prefix_number(task_crud)
    # set due date as end of the current year
    due_date = datetime.today().replace(month=12, day=31)
    for document in documents:
        if document.task:
            logger.warning(f"The document board ({board.id=}) already have default task added")
            continue
        max_prefix_counter += 1
        if start_external_id:
            external_id = handler._get_external_task_id(start_external_id, max_prefix_counter)
        else:
            external_id = handler.generate_task_external_id(task_crud, max_prefix_counter=max_prefix_counter)
        task_payload = {
            "name": document.name.value,
            "external_id": external_id,
            "board_id": board.id,
            "status_id": default_status.id,
            "due_date": due_date,
            "creator_id": creator_id,
            "document_id": document.id,
        }
        default_document_tasks.append(task_payload)
    task_crud.create_items(default_document_tasks)
    logger.info(f"Created default tasks with for site documents board, board id={board.id}")
