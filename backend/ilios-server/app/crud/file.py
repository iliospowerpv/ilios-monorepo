from typing import List, Optional

from sqlalchemy.sql.functions import coalesce, concat

from app.crud.base_crud import BaseCRUD
from app.models.file import File
from app.models.user import User


class FileCRUD(BaseCRUD):
    """CRUD operations on Due Diligence File model."""

    def __init__(self, db_session):
        super().__init__(model=File, db_session=db_session)

    def get_by_filename(self, filename: str) -> Optional[File]:
        return self.db_session.query(self.model).filter_by(filename=filename).first()

    def get_document_files(self, document_id: int) -> List[File]:
        """Get files for document. Always order by created_at DESC."""
        query = self.db_session.query(
            self.model.id,
            self.model.filename,
            self.model.created_at,
            self.model.is_actual,
            self.model.version_number,
            self.model.version_label,
            concat(coalesce(User.first_name, "Deleted"), " ", coalesce(User.last_name, "User")).label("author"),
        )
        query = query.filter_by(document_id=document_id, deleted=False)
        query = query.outerjoin(User)
        query = self._add_order_by(query, self.model.created_at, "desc")
        return query.all()

    def get_current_version(self, document_id: int) -> Optional[File]:
        return self.db_session.query(self.model).filter_by(
            document_id=document_id, is_actual=True, deleted=False
        ).first()

    def get_versions_for_document(self, document_id: int) -> List[File]:
        return self.db_session.query(self.model).filter_by(
            document_id=document_id, deleted=False
        ).order_by(self.model.created_at.desc()).all()
