from app.crud.base_crud import BaseCRUD
from app.models.telemetry import DASConnection


class DASConnectionCRUD(BaseCRUD):
    """CRUD operations on DASConnection model."""

    def __init__(self, db_session):
        super().__init__(model=DASConnection, db_session=db_session)

    def get_company_connection_by_name(self, company_id: int, connection_name: str):
        query = (
            self.db_session.query(self.model)
            .filter(self.model.company_id == company_id)
            .filter(self.model.name == connection_name)
        )
        return query.one_or_none()
