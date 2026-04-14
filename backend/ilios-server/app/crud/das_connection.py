import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import joinedload

from app.crud.base_crud import BaseCRUD
from app.db.base import Base
from app.models.company import Company
from app.models.telemetry import DASConnection, DASProvidersEnum

logger = logging.getLogger(__name__)


class DASConnectionCRUD(BaseCRUD):
    """CRUD operations on DASConnection model."""

    def __init__(self, db_session):
        super().__init__(model=DASConnection, db_session=db_session)

    def create_item(self, item: dict) -> Base:
        from app.crud.company_das_provider import CompanyDASProviderCRUD

        company_id = item.get("company_id")
        provider = item.get("provider")
        if company_id and provider:
            provider_enum = provider if isinstance(provider, DASProvidersEnum) else DASProvidersEnum(provider)
            if not CompanyDASProviderCRUD(self.db_session).has_provider(company_id, provider_enum):
                logger.warning(
                    f"Blocked DAS connection creation: provider '{provider}' not assigned to company {company_id}"
                )
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    f"Provider '{provider_enum.value}' is not assigned to this company. "
                    "Contact an administrator to configure available providers.",
                )
        return super().create_item(item)

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
        - Company-owned connections (owner_type='company', company_id matches)
        - Portfolio-shared connections (owner_type='portfolio', same hub)
        
        Args:
            company_id: The company ID to find hub connections for
            
        Returns:
            List of DASConnection objects accessible within the portfolio hub boundary
        """
        from app.helpers.portfolio_hub import resolve_company_hub_id, get_portfolio_group_company_ids
        
        company_connections = list(
            self.db_session.query(self.model)
            .filter(self.model.company_id == company_id)
            .filter(self.model.owner_type == "company")
            .all()
        )
        
        hub_id = resolve_company_hub_id(self.db_session, company_id)
        if hub_id is None:
            return company_connections
        
        hub_company_ids = get_portfolio_group_company_ids(self.db_session, hub_id)
        portfolio_connections = list(
            self.db_session.query(self.model)
            .filter(self.model.owner_type == "portfolio")
            .filter(self.model.owner_company_id.in_(hub_company_ids))
            .all()
        )
        
        return company_connections + portfolio_connections

    def get_available_connections_grouped(self, company_id: int) -> Dict[str, List[DASConnection]]:
        """Get connections grouped by ownership type for the wizard UI.
        
        Args:
            company_id: The company ID to find connections for
            
        Returns:
            Dict with 'company_connections' and 'portfolio_connections' lists
        """
        from app.helpers.portfolio_hub import resolve_company_hub_id, get_portfolio_group_company_ids
        
        company_connections = list(
            self.db_session.query(self.model)
            .options(joinedload(self.model.company))
            .filter(self.model.company_id == company_id)
            .filter(self.model.owner_type == "company")
            .order_by(self.model.name)
            .all()
        )
        
        hub_id = resolve_company_hub_id(self.db_session, company_id)
        portfolio_connections = []
        
        if hub_id is not None:
            hub_company_ids = get_portfolio_group_company_ids(self.db_session, hub_id)
            portfolio_connections = list(
                self.db_session.query(self.model)
                .options(joinedload(self.model.company), joinedload(self.model.owner_company))
                .filter(self.model.owner_type == "portfolio")
                .filter(self.model.owner_company_id.in_(hub_company_ids))
                .order_by(self.model.name)
                .all()
            )
        
        return {
            "company_connections": company_connections,
            "portfolio_connections": portfolio_connections,
        }

    def update_test_status(
        self,
        connection_id: int,
        status: str,
        message: Optional[str] = None
    ) -> None:
        """Update the last test status for a connection."""
        self.update_by_id(connection_id, {
            "last_test_at": datetime.utcnow(),
            "last_test_status": status,
            "last_test_message": message[:500] if message else None,
        })
