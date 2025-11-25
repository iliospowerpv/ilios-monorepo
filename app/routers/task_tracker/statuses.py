"""Module to manage board statuses"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.board_status import BoardStatusCRUD
from app.crud.errors import UniqueConstraintViolationError
from app.db.session import get_session
from app.helpers.authorization import (
    AssetPermissions,
    AuthorizedUser,
    DiligencePermissions,
    OnMPermissions,
    get_authorized_board,
    get_authorized_status,
)
from app.models.board import Board, BoardStatus
from app.schema.board_statuses import (
    BaseStatusSchema,
    StatusCreationSuccess,
    StatusListSchema,
    StatusNameUpdateSuccess,
    StatusRemovalSuccess,
)
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions

logger = logging.getLogger(__name__)
board_statuses_router = APIRouter()


@board_statuses_router.get(
    "/",
    response_model=StatusListSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.view),
                    DiligencePermissions(PermissionsActions.view),
                    OnMPermissions(PermissionsActions.view),
                ]
            )
        )
    ],
)
async def get_board_statuses(
    board: Board = Depends(get_authorized_board),
):
    return {"items": board.statuses}


@board_statuses_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=StatusCreationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit),
                    DiligencePermissions(PermissionsActions.edit),
                    OnMPermissions(PermissionsActions.edit),
                ]
            )
        )
    ],
)
async def create_board_status(
    status_payload: BaseStatusSchema,
    board: Board = Depends(get_authorized_board),
    db_session: Session = Depends(get_session),
):
    try:
        status_data = status_payload.model_dump()
        status_data["board_id"] = board.id
        board_status = BoardStatusCRUD(db_session).create_item(status_data)
        logger.info(f"Created status with id {board_status.id} on the board {board.id}")
    except UniqueConstraintViolationError:
        logger.error(f"Status with name '{status_payload.name}' already exists on the board with id {board.id}")
        raise HTTPException(status.HTTP_409_CONFLICT, "Status name should be unique across the board")
    return {"code": status.HTTP_201_CREATED, "message": "Status has been successfully created"}


@board_statuses_router.put(
    "/{status_id}/name",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StatusNameUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit),
                    DiligencePermissions(PermissionsActions.edit),
                    OnMPermissions(PermissionsActions.edit),
                ]
            )
        )
    ],
)
async def update_board_status_name(
    status_name_payload: BaseStatusSchema,
    board_status: BoardStatus = Depends(get_authorized_status),
    db_session: Session = Depends(get_session),
):
    try:
        BoardStatusCRUD(db_session).update_by_id(board_status.id, status_name_payload.model_dump())
    except UniqueConstraintViolationError:
        logger.error(
            f"Status with name '{status_name_payload.name}' already exists on the board with id {board_status.board.id}"
        )
        raise HTTPException(status.HTTP_409_CONFLICT, "Status name should be unique across the board")
    return {"code": status.HTTP_202_ACCEPTED, "message": "Status name has been successfully updated"}


@board_statuses_router.delete(
    "/{status_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=StatusRemovalSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit),
                    DiligencePermissions(PermissionsActions.edit),
                    OnMPermissions(PermissionsActions.edit),
                ]
            )
        )
    ],
)
async def remove_board_status(  # noqa: FNE008
    board_status: BoardStatus = Depends(get_authorized_status),
    db_session: Session = Depends(get_session),
):
    # validate if status has attached tasks
    if board_status.tasks:
        logger.warning(f"Cannot remove status with id {board_status.id}: {len(board_status.tasks)} tasks attached")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Status is in use, please, remove it from the tasks")
    BoardStatusCRUD(db_session).delete_by_id(board_status.id)
    return {"code": status.HTTP_202_ACCEPTED, "message": "Status has been successfully deleted"}
