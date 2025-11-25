from app.crud.base_crud import BaseCRUD
from app.models.board import Board


class BoardCRUD(BaseCRUD):
    """CRUD operations on Board model."""

    def __init__(self, db_session):
        super().__init__(model=Board, db_session=db_session)
