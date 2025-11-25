from typing import List

from sqlalchemy.sql.functions import coalesce, concat

from app.crud.base_crud import BaseCRUD
from app.models.file import File
from app.models.user import User


class FileCRUD(BaseCRUD):
    """CRUD operations on Due Diligence File model."""

    def __init__(self, db_session):
        super().__init__(model=File, db_session=db_session)

    def get_by_filename(self, filename: str) -> File:
        return self.db_session.query(self.model).filter_by(filename=filename).first()

    def get_document_files(self, document_id: int) -> List[File]:
        """Get files for document. Always order by created_at DESC."""
        query = self.db_session.query(
            self.model.id,
            self.model.filename,
            self.model.created_at,
            self.model.is_actual,
            concat(coalesce(User.first_name, "Deleted"), " ", coalesce(User.last_name, "User")).label("author"),
        )
        query = query.filter_by(document_id=document_id, deleted=False)
        query = query.outerjoin(User)
        query = self._add_order_by(query, self.model.created_at, "desc")
        return query.all()
