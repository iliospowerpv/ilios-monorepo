from datetime import timedelta

from app.crud.user_invitation import UserInvitationCRUD
from app.helpers.base_user_handler import UserPasswordDeeplinkBaseHandler
from app.models.helpers import utcnow
from app.settings import settings


class UserInvitationsHandler(UserPasswordDeeplinkBaseHandler):
    """Manage user invites transactional objects"""

    def __init__(self, db_session, user):
        super().__init__(user=user)
        self.user_invitation_crud = UserInvitationCRUD(db_session)

    def _set_expires_at(self):
        self.expires_at = utcnow() + timedelta(days=settings.invitation_link_expire_days)

    def create_invitation_object(self):
        """Creates invitation object for specified user."""
        self.user_invitation_crud.create_item(self._build_user_object())

    def _update_invitation_object(self, invitation_id):
        """Updates invitation object for specified user."""
        self.user_invitation_crud.update_by_id(target_id=invitation_id, item=self._build_user_object())

    def update_invitation_object(self):
        """Updates existing object or create a new one"""
        # honestly, I'm not sure that it's possible, but let's be on the safe side and handle the case
        if not self.user.invitation:
            return self.create_invitation_object()

        # update invitation if it exists
        return self._update_invitation_object(invitation_id=self.user.invitation[0].id)
