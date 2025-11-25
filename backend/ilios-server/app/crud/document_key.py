from app.crud.base_crud import BaseCRUD
from app.models.document import DocumentKey


class DocumentKeyCRUD(BaseCRUD):
    """CRUD operations on Due Diligence DocumentKey model."""

    def __init__(self, db_session):
        super().__init__(model=DocumentKey, db_session=db_session)

    def get_document_key(self, name: str, document_id: int):
        return self.db_session.query(self.model).filter_by(name=name, document_id=document_id).first()

    def get_document_keys_by_names(self, document_id: int, keys_names: list):
        return (
            self.db_session.query(self.model)
            .filter(self.model.name.in_(keys_names), self.model.document_id == document_id)
            .all()
        )
