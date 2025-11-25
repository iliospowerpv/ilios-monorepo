"""Module to manage boards"""

import logging

from fastapi import APIRouter, Depends, status
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.board import BoardCRUD
from app.crud.board_related_entity import BoardRelatedEntityCRUD
from app.db.session import get_session
from app.filters.user_filters import UserSearchForTaskFilter
from app.helpers.authorization import (
    AssetPermissions,
    AuthorizedUser,
    DiligencePermissions,
    OnMPermissions,
    get_authorized_board,
    validate_board_related_entity_permissions,
)
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_skip_and_limit
from app.helpers.task_tracker import TaskTrackerHandlerFactory
from app.models.board import Board, BoardModuleEnum, BoardRelatedEntityTypeEnum
from app.schema.board import (
    BoardBaseSchema,
    BoardCreateSchema,
    BoardCreationSuccess,
    BoardRemovalSuccess,
    BoardsPageSchema,
    BoardsPaginator,
    BoardUpdateSuccess,
)
from app.schema.site import PotentialTaskAssigneeList
from app.static import (
    DEFAULT_PAGINATION_LIMIT,
    DEFAULT_PAGINATION_SKIP,
    HTTP_403_RESPONSE,
    HTTP_404_RESPONSE,
    PermissionsActions,
)

logger = logging.getLogger(__name__)
board_router = APIRouter()


@board_router.get(
    "/",
    dependencies=[
        Depends(validate_board_related_entity_permissions),
        Depends(validate_skip_and_limit),
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.view),
                    DiligencePermissions(PermissionsActions.view),
                    OnMPermissions(PermissionsActions.view),
                ]
            )
        ),
    ],
    response_model=BoardsPaginator,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Retrieve board by related entity and module, module is set to 'asset' by default",
)
async def get_entity_boards(
    entity_type: BoardRelatedEntityTypeEnum,
    entity_id: int,
    module: BoardModuleEnum = BoardModuleEnum.asset,
    skip: int = DEFAULT_PAGINATION_SKIP,
    limit: int = DEFAULT_PAGINATION_LIMIT,
    db_session: Session = Depends(get_session),
):
    total, boards = BoardRelatedEntityCRUD(db_session).get_by_entity(
        entity_type=entity_type, entity_id=entity_id, skip=skip, limit=limit, module=module
    )
    return {"items": boards, **pagination_details(skip, limit, total)}


@board_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=BoardCreationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(validate_board_related_entity_permissions),
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.edit),
                    DiligencePermissions(PermissionsActions.edit),
                    OnMPermissions(PermissionsActions.edit),
                ]
            )
        ),
    ],
)
async def create_new_board(
    entity_type: BoardRelatedEntityTypeEnum,
    entity_id: int,
    board_payload: BoardCreateSchema,
    db_session: Session = Depends(get_session),
):
    # create board instance
    board = BoardCRUD(db_session).create_item(board_payload.model_dump())
    # link board with related entity
    related_entity = BoardRelatedEntityCRUD(db_session).create_item(
        {"entity_id": entity_id, "entity_type": entity_type, "board_id": board.id}
    )

    logger.info(
        f"Created board with id {board.id} and link it to related_entity '{entity_type}' with id {related_entity.id}"
    )
    return {"code": status.HTTP_201_CREATED, "message": "Board has been successfully created"}


@board_router.get(
    "/{board_id}",
    response_model=BoardsPageSchema,
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
async def get_board_by_id(
    board: Board = Depends(get_authorized_board),
):
    return board


@board_router.put(
    "/{board_id}",
    response_model=BoardUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Update board name|description|is_active",
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
async def update_board(
    board_payload: BoardBaseSchema,
    board: Board = Depends(get_authorized_board),
    db_session: Session = Depends(get_session),
):
    BoardCRUD(db_session).update_by_id(board.id, board_payload.model_dump())
    return {"code": status.HTTP_200_OK, "message": "Board has been successfully updated"}


@board_router.delete(
    "/{board_id}",
    response_model=BoardRemovalSuccess,
    status_code=status.HTTP_202_ACCEPTED,
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
async def delete_board_by_id(
    board: Board = Depends(get_authorized_board),
    db_session: Session = Depends(get_session),
):
    BoardCRUD(db_session).delete_by_id(board.id)
    return {"code": status.HTTP_200_OK, "message": "Board has been successfully deleted"}


@board_router.get(
    "/{board_id}/assignees",
    response_model=PotentialTaskAssigneeList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Potential users list for Task assignee.",
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
async def get_potential_task_assignees(
    board: Board = Depends(get_authorized_board),
    search_user_filter: UserSearchForTaskFilter = FilterDepends(UserSearchForTaskFilter),
    task_id: int = None,
    db_session: Session = Depends(get_session),
):
    handler = TaskTrackerHandlerFactory(db_session).get_instance(board)
    return {"items": handler.get_assignees(search_user_filter, task_id)}
