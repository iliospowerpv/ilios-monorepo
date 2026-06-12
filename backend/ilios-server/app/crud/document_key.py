from typing import Optional

from app.crud.base_crud import BaseCRUD
from app.models.document import DocumentKey


class DocumentKeyCRUD(BaseCRUD):
    """CRUD operations on Due Diligence DocumentKey model."""

    def __init__(self, db_session):
        super().__init__(model=DocumentKey, db_session=db_session)

    def get_document_key(self, name: str, document_id: int, file_id: Optional[int] = None):
        query = self.db_session.query(self.model).filter_by(name=name, document_id=document_id)
        if file_id is not None:
            query = query.filter_by(file_id=file_id)
        return query.first()

    def get_keys_for_file(self, file_id: int) -> list[DocumentKey]:
        return self.db_session.query(self.model).filter_by(file_id=file_id).all()

    def get_accepted_keys_for_file(self, file_id: int) -> list[DocumentKey]:
        return self.db_session.query(self.model).filter(
            self.model.file_id == file_id,
            self.model.status.in_(["accepted", "overridden"])
        ).all()
