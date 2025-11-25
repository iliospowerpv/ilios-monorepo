from datetime import timedelta

from app.crud.user_password_recovery import UserPasswordRecoveryCRUD
from app.helpers.base_user_handler import UserPasswordDeeplinkBaseHandler
from app.models.helpers import utcnow
from app.settings import settings


class UserPasswordRecoveryHandler(UserPasswordDeeplinkBaseHandler):
    """Manage user password reset transactional objects"""

    def __init__(self, db_session, user):
        super().__init__(user=user)
        self.user_password_crud = UserPasswordRecoveryCRUD(db_session)

    def _set_expires_at(self):
        self.expires_at = utcnow() + timedelta(minutes=settings.reset_password_expires_minutes)

    def create_password_recovery_object(self):
        """Creates password reset object for specified user."""
        self.user_password_crud.create_item(self._build_user_object())

    def _update_password_recovery_object(self, invitation_id):
        """Updates password reset object for specified user."""
        self.user_password_crud.update_by_id(target_id=invitation_id, item=self._build_user_object())

    def update_password_recovery_object(self):
        """Updates existing password reset object or create a new one"""
        if not self.user.password_recovery:
            return self.create_password_recovery_object()

        return self._update_password_recovery_object(invitation_id=self.user.password_recovery[0].id)
