from typing import List

from app.crud.base_crud import BaseCRUD
from app.models.company import Company
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

    def get_hub_connections(self, company_id: int) -> List[DASConnection]:
        """Get all DAS connections accessible to a company through portfolio hub.
        
        This includes:
        - Connections owned by the company itself
        - Connections from other companies in the same portfolio hub (shared connections)
        
        Args:
            company_id: The company ID to find hub connections for
            
        Returns:
            List of DASConnection objects accessible within the portfolio hub boundary
        """
        from app.helpers.portfolio_hub import resolve_company_hub_id, get_portfolio_group_company_ids
        
        hub_id = resolve_company_hub_id(self.db_session, company_id)
        if hub_id is None:
            return list(self.db_session.query(self.model).filter(self.model.company_id == company_id).all())
        
        hub_company_ids = get_portfolio_group_company_ids(self.db_session, hub_id)
        return list(
            self.db_session.query(self.model)
            .filter(self.model.company_id.in_(hub_company_ids))
            .order_by(self.model.company_id, self.model.name)
            .all()
        )
