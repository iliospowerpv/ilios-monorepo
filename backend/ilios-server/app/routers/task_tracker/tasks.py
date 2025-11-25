import logging
from copy import deepcopy
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.errors import UniqueConstraintViolationError
from app.crud.task import TaskCRUD
from app.db.session import get_session
from app.filters.task_filters import SearchTaskByName
from app.helpers.authorization import (
    AssetPermissions,
    AuthorizedUser,
    DiligencePermissions,
    OnMPermissions,
    get_authorized_board,
    get_authorized_task,
)
from app.helpers.notification_helper import NotificationHandler
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.helpers.task_tracker import TaskTrackerHandlerFactory
from app.models.board import Board, BoardModuleEnum, BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.models.notification import NotificationKindsEnum, NotificationSubjectsEnum
from app.models.task import Task
from app.schema.task import (
    TaskCreationPayloadSchema,
    TaskCreationSuccess,
    TaskDescriptionUpdateSchema,
    TaskDetailsUpdateSchema,
    TaskDetailsViewSchema,
    TaskOrderByFieldEnum,
    TasksListResponse,
    TaskSummaryOfEventUpdateSchema,
    TaskUpdateSuccess,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions, TaskMessages

logger = logging.getLogger(__name__)
tasks_router = APIRouter()


@tasks_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskCreationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def create(
    task: TaskCreationPayloadSchema,
    current_user: Annotated[
        CurrentUserSchema,
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
    board: Board = Depends(get_authorized_board),
    db_session: Session = Depends(get_session),
):
    handler = TaskTrackerHandlerFactory(db_session).get_instance(board)
    if board.related_entity.extra_entity_type == BoardRelatedEntityTypeExtraEnum.document:
        logger.warning("Temporary limitation: can not create tasks for documents board")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Task adding to the Document level boards is prohibited"
        )
    handler.validate_task_related_entities_existence(task)
    handler.validate_task_due_date(task)

    task_crud = TaskCRUD(db_session)
    # add system fields
    task_payload = task.model_dump()
    task_payload["creator_id"] = current_user.id
    task_payload["board_id"] = board.id

    # generate task external ID as Prefix + Number
    task_payload["external_id"] = handler.generate_task_external_id(task_crud)

    try:
        task = task_crud.create_item(task_payload)
    except UniqueConstraintViolationError:
        logger.exception(message := TaskMessages.alert_task_already_exists)
        raise HTTPException(status.HTTP_409_CONFLICT, message)
    logger.info(f"Created task with id {task.id} on the board {board.id}")
    return {"code": status.HTTP_201_CREATED, "message": TaskMessages.task_create_success, "entity_id": task.id}


@tasks_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=TasksListResponse,
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
async def get_board_tasks(
    query_params: tuple = Depends(validate_query_params(order_by=TaskOrderByFieldEnum)),
    site_filter: SearchTaskByName = FilterDepends(SearchTaskByName),
    board: Board = Depends(get_authorized_board),
    db_session: Session = Depends(get_session),
):
    skip, limit, order_by, order_direction = query_params
    total, tasks = TaskCRUD(db_session).get_tasks_by_board_id(
        board.id, site_filter, skip, limit, order_by, order_direction
    )
    return {"items": tasks, **pagination_details(skip, limit, total)}


@tasks_router.get(
    "/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=TaskDetailsViewSchema,
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
async def get_by_id(
    task: Task = Depends(get_authorized_task),
):
    return task


@tasks_router.put(
    "/{task_id}/description",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskUpdateSuccess,
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
async def description_update(
    description: TaskDescriptionUpdateSchema,
    task: Task = Depends(get_authorized_task),
    db_session: Session = Depends(get_session),
):
    TaskCRUD(db_session).update_by_id(task.id, description.model_dump())
    return {"code": status.HTTP_202_ACCEPTED, "message": TaskMessages.task_update_success}


@tasks_router.put(
    "/{task_id}/summary-of-events",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskUpdateSuccess,
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
async def summary_of_event_update(
    payload: TaskSummaryOfEventUpdateSchema,
    task: Task = Depends(get_authorized_task),
    db_session: Session = Depends(get_session),
):
    if task.board.module not in [BoardModuleEnum.asset, BoardModuleEnum.om]:
        logger.warning(f"Cannot set <summary of events> section for task of board type <{task.board.module}>")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, TaskMessages.summary_of_event_not_applicable)

    TaskCRUD(db_session).update_by_id(task.id, payload.model_dump())
    return {"code": status.HTTP_202_ACCEPTED, "message": TaskMessages.task_update_success}


@tasks_router.put(
    "/{task_id}/details",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=TaskUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def details_update(
    task_details: TaskDetailsUpdateSchema,
    current_user: Annotated[
        CurrentUserSchema,
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
    task: Task = Depends(get_authorized_task),
    db_session: Session = Depends(get_session),
):
    # make a snapshot of task for difference comparison, changes after update will be reflected in the 'task' object
    original_task = deepcopy(task)

    # Make sure affected device applicable only for the site level boards
    if (
        task.board.related_entity.entity_type != BoardRelatedEntityTypeEnum.site
        or task.board.related_entity.entity_type == BoardRelatedEntityTypeExtraEnum.document
    ):
        task_details.affected_device_id = None

    handler = TaskTrackerHandlerFactory(db_session).get_instance(task.board)
    handler.validate_updated_task_related_entities(task, task_details)

    TaskCRUD(db_session).update_by_id(task.id, task_details.model_dump())

    # analyze changes to create notifications
    notifications_handler = NotificationHandler(
        db_session=db_session,
        actor=current_user,
        notification_subject=NotificationSubjectsEnum.task,
        notification_subject_id=task.id,
    )
    # status changes - notify creator
    if original_task.status_id != task.status_id:
        notifications_handler.save_notification(
            recipient_id=task.creator_id,
            kind=NotificationKindsEnum.task_status_change,
            extra={"status_id": task.status_id},
        )
        handler.update_task_completion_details(task)
    # assignee change - several scenarios
    if original_task.assignee_id != task.assignee_id:
        if task.assignee_id is None:
            # task unassigned - notify creator
            notifications_handler.save_notification(
                recipient_id=task.creator_id,
                kind=NotificationKindsEnum.task_assignee_unset,
                extra={"previous_assignee_id": original_task.assignee_id},
            )
        else:
            # notify new assignee about the task in their inbox
            notifications_handler.save_notification(
                recipient_id=task.assignee_id, kind=NotificationKindsEnum.task_assignee_added
            )
            # notify creator as well if ticket was re-assigned
            if original_task.assignee_id is not None:
                notifications_handler.save_notification(
                    recipient_id=task.creator_id,
                    kind=NotificationKindsEnum.task_assignee_changed,
                    extra={"new_assignee_id": task.assignee_id},
                )

    return {"code": status.HTTP_202_ACCEPTED, "message": TaskMessages.task_update_success}
