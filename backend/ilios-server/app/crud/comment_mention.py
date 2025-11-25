from app.crud.base_crud import BaseCRUD
from app.models.comment import CommentMention


class CommentMentionCRUD(BaseCRUD):
    """CRUD operations on CommentMention model."""

    def __init__(self, db_session):
        super().__init__(model=CommentMention, db_session=db_session)
