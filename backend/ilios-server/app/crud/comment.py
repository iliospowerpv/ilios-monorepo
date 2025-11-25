from app.crud.base_crud import BaseCRUD
from app.models.comment import Comment


class CommentCRUD(BaseCRUD):
    """CRUD operations on Comment model."""

    def __init__(self, db_session):
        super().__init__(model=Comment, db_session=db_session)
