import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.board import BoardCRUD
from app.crud.board_status import BoardStatusCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_company, get_authorized_site, validate_entity_exists
from app.models.board import Board, BoardRelatedEntityTypeEnum
from app.schema.user import CurrentUserSchema

logger = logging.getLogger(__name__)


BOARD_RELATED_ENTITY_MAPPER = {
    BoardRelatedEntityTypeEnum.site: get_authorized_site,
    BoardRelatedEntityTypeEnum.company: get_authorized_company,
}


def validate_board_related_entity_permissions(
    entity_id: int,
    entity_type: BoardRelatedEntityTypeEnum,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Validate current user's permissions to access the board related entity: company, site, document, etc."""
    related_entity_getter = BOARD_RELATED_ENTITY_MAPPER.get(entity_type, None)
    return related_entity_getter(entity_id, current_user, db_session) if related_entity_getter else None


def get_authorized_board(
    board_id,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Get board object and validate user has access to it parent entity"""
    # check board exists
    board = BoardCRUD(db_session).get_by_id(board_id)
    validate_entity_exists(board, board_id, "board")
    # check user has access to it
    validate_board_related_entity_permissions(
        board.related_entity.entity_id, board.related_entity.entity_type, current_user, db_session
    )
    # finally, return the board object
    return board


def get_authorized_status(
    status_id,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    board: Board = Depends(get_authorized_board),
):
    """Get status and validate user has access to the parent board"""
    # check board status exists
    board_status = BoardStatusCRUD(db_session).get_by_id(status_id)
    validate_entity_exists(board_status, status_id, "status")
    # check status belongs to the board from the request
    if board_status.board_id != board.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access status {status_id} which attached to different board"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return board_status
