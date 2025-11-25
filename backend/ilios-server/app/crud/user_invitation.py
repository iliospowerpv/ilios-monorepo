"""CRUD operations on UserInvitation model."""

from app.crud.base_crud import BaseCRUD
from app.models.user import UserInvitation


class UserInvitationCRUD(BaseCRUD):
    """CRUD operations on UserInvitation model."""

    def __init__(self, db_session):
        super().__init__(model=UserInvitation, db_session=db_session)

    def get_by_token(self, token):
        return self.db_session.query(self.model).filter_by(token=token).scalar()
