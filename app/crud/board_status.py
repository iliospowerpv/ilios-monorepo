from app.crud.base_crud import BaseCRUD
from app.models.board import BoardStatus


class BoardStatusCRUD(BaseCRUD):
    """CRUD operations on BoardStatus model."""

    def __init__(self, db_session):
        super().__init__(model=BoardStatus, db_session=db_session)
