import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.site_visit import SiteVisitCRUD
from app.db.session import get_session
from app.helpers.authorization import (
    AuthorizedUser,
    OnMPermissions,
    get_authorized_site_visit,
    get_authorized_site_visit_task,
)
from app.models.site_visit import SiteVisit
from app.models.task import Task
from app.schema.site_visit import SiteVisitCreationSuccess, SiteVisitSchema, SiteVisitUpdateSuccess
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions, TaskMessages

logger = logging.getLogger(__name__)
site_visits_router = APIRouter()


@site_visits_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=SiteVisitCreationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def create(
    current_user: Annotated[
        CurrentUserSchema,
        Depends(
            AuthorizedUser(
                [
                    OnMPermissions(PermissionsActions.edit),
                ]
            )
        ),
    ],
    task: Task = Depends(get_authorized_site_visit_task),
    db_session: Session = Depends(get_session),
):
    if task.site_visit:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=TaskMessages.multiple_site_visits_error)

    site_visit_object = SiteVisitCRUD(db_session=db_session).create_item(
        {
            "task_id": task.id,
            "creator_id": current_user.id,
        }
    )

    logger.info(f"Created site visit object <{site_visit_object.id}> for the task with id <{task.id}>")
    return {"code": status.HTTP_201_CREATED, "message": TaskMessages.site_visit_create_success}


@site_visits_router.put(
    "",
    status_code=status.HTTP_200_OK,
    response_model=SiteVisitUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    OnMPermissions(PermissionsActions.view),
                ]
            )
        )
    ],
)
async def update(
    site_visit_payload: SiteVisitSchema,
    site_visit: SiteVisit = Depends(get_authorized_site_visit),
    db_session: Session = Depends(get_session),
):
    SiteVisitCRUD(db_session=db_session).update_by_id(site_visit.id, site_visit_payload.model_dump())

    return {"code": status.HTTP_200_OK, "message": TaskMessages.site_visit_update_success}


@site_visits_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=SiteVisitSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    OnMPermissions(PermissionsActions.view),
                ]
            )
        )
    ],
)
async def get(
    site_visit: SiteVisit = Depends(get_authorized_site_visit),
):
    return site_visit
