from app.crud.base_crud import BaseCRUD
from app.models.document import Document


class DocumentCRUD(BaseCRUD):
    """CRUD operations on Due Diligence Document model."""

    def __init__(self, db_session):
        super().__init__(model=Document, db_session=db_session)

    def get_site_documents_ordered_by_name(self, site_id, order_by: str = "name"):
        query = self.db_session.query(self.model)
        query = query.filter(self.model.site_id == site_id)
        query = self._add_order_by(query, order_by, "asc")
        return query.all()
