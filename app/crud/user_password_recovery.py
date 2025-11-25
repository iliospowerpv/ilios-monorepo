"""CRUD operations on UserPasswordRecovery model."""

from app.crud.base_crud import BaseCRUD
from app.models.user import UserPasswordRecovery


class UserPasswordRecoveryCRUD(BaseCRUD):
    """CRUD operations on UserPasswordRecovery model."""

    def __init__(self, db_session):
        super().__init__(model=UserPasswordRecovery, db_session=db_session)

    def get_by_token(self, token):
        return self.db_session.query(self.model).filter_by(token=token).scalar()
