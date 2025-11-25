from app.crud.base_crud import BaseCRUD
from app.models.document import DocumentSection
from app.static.default_site_documents_enum import DocumentSections


class DocumentSectionCRUD(BaseCRUD):
    """CRUD operations on Due Diligence DocumentSection model."""

    def __init__(self, db_session):
        super().__init__(model=DocumentSection, db_session=db_session)

    def drop_site_default_sections(self, site_ids: list):
        self.db_session.query(self.model).filter(
            (self.model.site_id.in_(site_ids)) & (self.model.name.in_(list(DocumentSections)))
        ).delete()
        self.db_session.commit()

    def get_site_sections(self, site_id: list) -> list:
        query = self.db_session.query(self.model)
        query = query.filter(self.model.site_id == site_id)
        query = self._add_order_by(query, self.model.position, "asc")
        return query.all()
