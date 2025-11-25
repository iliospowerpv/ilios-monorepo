import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app import static
from app.crud.notification import NotificationCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import get_authorized_notification
from app.helpers.notification_helper import NotificationReadHandler
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_skip_and_limit
from app.models.notification import Notification
from app.models.session import Session
from app.schema.notification import (
    NotificationDeleteSuccessSchema,
    NotificationsListSchema,
    NotificationUpdateSuccessSchema,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, NotificationMessages

logger = logging.getLogger(__name__)
dashboard_notifications_router = APIRouter()


@dashboard_notifications_router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=NotificationsListSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(validate_skip_and_limit)],
    description="API to retrieve all notifications where the recipient is the logged in user",
)
async def get_notifications(
    skip: int = static.DEFAULT_PAGINATION_SKIP,
    limit: int = static.DEFAULT_PAGINATION_LIMIT,
    *,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    total, unread_count, items = NotificationCRUD(db_session).get_notifications_by_user(
        current_user.id, skip=skip, limit=limit
    )
    for item in items:
        # NOTE! For the future developers:
        # currently post-processing makes additional DB call to retrieve notification subject from DB
        # (because we unlink notification from a task and notifications are related to other entities via extra-table,
        # which doesn't have FK to the related object)
        # it's fine, since we have notifications list paginated and UI requests only 5 items per dashboard.
        # If you face with the performance degradation - it can be optimized from DB calls perspective
        # by retrieving full list of subjects for notifications which we should serve and
        # then filter out proper object: for example, if you have 3 comment notification and 3 task notifications,
        # rather than making 6 DB calls in the notification handler
        # you can retrieve it by 2 DB calls to corresponding tables
        NotificationReadHandler(item, db_session).extend_with_additional_fields()

    return {"items": items, "unread_count": unread_count, **pagination_details(skip, limit, total)}


@dashboard_notifications_router.patch(
    "/{notification_id}/seen",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=NotificationUpdateSuccessSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="API to mark notification as read",
)
async def mark_as_read(
    notification: Notification = Depends(get_authorized_notification),
    db_session: Session = Depends(get_session),
):
    NotificationCRUD(db_session).update_by_id(notification.id, {"seen": True})
    return {"code": status.HTTP_202_ACCEPTED, "message": NotificationMessages.mark_as_read_success}


@dashboard_notifications_router.delete(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
    response_model=NotificationDeleteSuccessSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Hard delete user notification",
)
async def delete(
    notification: Notification = Depends(get_authorized_notification),
    db_session: Session = Depends(get_session),
):
    NotificationCRUD(db_session).delete_by_id(notification.id)
    return {"code": status.HTTP_200_OK, "message": NotificationMessages.delete_success}
