from app.crud.base_crud import BaseCRUD
from app.models.auth_security_event import AuthSecurityEvent


class AuthSecurityEventCRUD(BaseCRUD):
    """CRUD operations on AuthSecurityEvent model."""

    def __init__(self, db_session):
        super().__init__(model=AuthSecurityEvent, db_session=db_session)
