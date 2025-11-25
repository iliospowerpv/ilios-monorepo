import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app import static
from app.crud.task import TaskCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_skip_and_limit
from app.models.board import BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.models.session import Session
from app.schema.task import UserTasksListResponse
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
dashboard_tasks_router = APIRouter()


@dashboard_tasks_router.get(
    "/tasks",
    status_code=status.HTTP_200_OK,
    response_model=UserTasksListResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(validate_skip_and_limit)],
    description="API to retrieve all tasks assigned to the logged in user",
)
async def get_user_tasks(
    skip: int = static.DEFAULT_PAGINATION_SKIP,
    limit: int = static.DEFAULT_PAGINATION_LIMIT,
    *,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    total, user_tasks = TaskCRUD(db_session).get_user_tasks(current_user.id, skip=skip, limit=limit)
    for user_task in user_tasks:
        # set module based on the parent object
        user_task.module = user_task.board.module
        if user_task.board.related_entity.entity_type == BoardRelatedEntityTypeEnum.site:
            if user_task.board.related_entity.extra_entity_type == BoardRelatedEntityTypeExtraEnum.document:
                """Task already has relation to document no need for additional DB call"""
            else:
                user_task.site = user_task.board.related_entity.parent_entity_site
        if user_task.board.related_entity.entity_type == BoardRelatedEntityTypeEnum.company:
            user_task.company = user_task.board.related_entity.parent_entity_company
    return {"items": user_tasks, **pagination_details(skip, limit, total)}
