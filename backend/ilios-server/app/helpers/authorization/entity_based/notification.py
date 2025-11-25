import logging

from fastapi import Depends, HTTPException, status

from app.crud.notification import NotificationCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import validate_entity_exists

logger = logging.getLogger(__name__)


def get_authorized_notification(
    notification_id: int,
    current_user=Depends(get_current_user),
    db_session=Depends(get_session),
):
    """Get notification object and validate user has access to it."""
    # check notification exists
    notification = NotificationCRUD(db_session).get_by_id(notification_id)
    validate_entity_exists(notification, notification_id, "notification")
    # check user has access to it
    if notification.recipient_id != current_user.id:
        logger.warning(
            f"Scope mismatch! "
            f"User {current_user.id} tried to access notification {notification_id} which attached to different user"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return notification
