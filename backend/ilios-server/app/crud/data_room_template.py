from app.crud.base_crud import BaseCRUD
from app.models.data_room_template import DataRoomTemplate


class DataRoomTemplateCRUD(BaseCRUD):
    """CRUD operations on the company-scoped Data Room Template model (Task #91)."""

    def __init__(self, db_session):
        super().__init__(model=DataRoomTemplate, db_session=db_session)

    def get_by_company(self, company_id: int, include_archived: bool = False):
        query = self.db_session.query(self.model).filter(self.model.company_id == company_id)
        if not include_archived:
            query = query.filter(self.model.is_archived.is_(False))
        return query.order_by(self.model.name.asc()).all()

    def get_for_company(self, template_id: int, company_id: int):
        """Return a template only when it belongs to the given company (scope guard)."""
        return (
            self.db_session.query(self.model)
            .filter(self.model.id == template_id, self.model.company_id == company_id)
            .one_or_none()
        )
