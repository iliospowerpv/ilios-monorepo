from app.crud.base_crud import BaseCRUD
from app.models.file import AIParsingResult


class AIParsingResultCRUD(BaseCRUD):
    """CRUD operations on AIParsingResult model."""

    def __init__(self, db_session):
        super().__init__(model=AIParsingResult, db_session=db_session)
