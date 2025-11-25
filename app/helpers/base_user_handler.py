from abc import ABC, abstractmethod
from secrets import token_urlsafe


class UserPasswordDeeplinkBaseHandler(ABC):
    """User base handler for invitations and password reset"""

    def __init__(self, user):
        self.user = user
        self._set_token()
        self._set_expires_at()

    @abstractmethod
    def _set_expires_at(self):
        """Abstract method to set token expiration for user invitation and password recovery"""

    def _set_token(self):
        self.token = token_urlsafe(64)

    def _build_user_object(self):
        return {
            "user_id": self.user.id,
            "token": self.token,
            "expires_at": self.expires_at,
        }
