"""Populates DB with pre-defined data."""

import logging

from sqlalchemy.orm import Session

from app.crud.user import UserCRUD
from app.helpers.authentication import get_password_hash
from app.settings import settings

logger = logging.getLogger(__name__)


class AppInitHelper:

    def __init__(self, db: Session):
        self.session = db

    def set_predefined_data(self):
        self._create_system_user()

    def _create_system_user(self):
        """Create system user if it doesn't exist yet"""
        user_data = {
            "email": settings.system_user_email,
            "hashed_password": get_password_hash(settings.system_user_password),
            "first_name": settings.system_user_first_name,
            "last_name": settings.system_user_last_name,
            "is_system_user": True,
            "is_registered": True,
            "phone": settings.system_user_phone,
        }
        user_crud_helper = UserCRUD(self.session)
        user = user_crud_helper.get_by_email(user_data["email"])
        if not user:
            user_crud_helper.create_item(user_data)
            logger.debug(f"Created a system user with email={user_data['email']}")
