"""CRUD operations for FinanceIntegration model."""

from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.finance_integration import FinanceIntegration, FinanceIntegrationStatus
from app.services.finance.credential_helper import encrypt_credentials, decrypt_credentials


class FinanceIntegrationCRUD(BaseCRUD):
    """CRUD operations for FinanceIntegration model."""

    def __init__(self, db_session: Session):
        super().__init__(model=FinanceIntegration, db_session=db_session)

    def get_by_company(self, company_id: int) -> List[FinanceIntegration]:
        """Get all finance integrations for a company.
        
        Args:
            company_id: The company ID.
            
        Returns:
            List of FinanceIntegration objects.
        """
        return (
            self.db_session.query(FinanceIntegration)
            .filter(FinanceIntegration.company_id == company_id)
            .all()
        )

    def get_by_company_and_provider(
        self, company_id: int, provider_key: str
    ) -> Optional[FinanceIntegration]:
        """Get a specific finance integration by company and provider.
        
        Args:
            company_id: The company ID.
            provider_key: The provider key (e.g., 'gravity').
            
        Returns:
            FinanceIntegration or None.
        """
        return (
            self.db_session.query(FinanceIntegration)
            .filter(
                FinanceIntegration.company_id == company_id,
                FinanceIntegration.provider_key == provider_key,
            )
            .first()
        )

    def create_integration(
        self,
        company_id: int,
        provider_key: str,
        credentials: dict,
        config: Optional[dict] = None,
        created_by_user_id: Optional[int] = None,
    ) -> FinanceIntegration:
        """Create a new finance integration.
        
        Args:
            company_id: The company ID.
            provider_key: The provider key.
            credentials: The provider credentials (will be encrypted).
            config: Optional configuration dictionary.
            created_by_user_id: ID of the user creating the integration.
            
        Returns:
            The created FinanceIntegration.
        """
        encrypted_creds = encrypt_credentials(credentials) if credentials else None
        
        integration = FinanceIntegration(
            company_id=company_id,
            provider_key=provider_key,
            encrypted_credentials=encrypted_creds,
            config_json=config,
            status=FinanceIntegrationStatus.pending,
            created_by_user_id=created_by_user_id,
            updated_by_user_id=created_by_user_id,
        )
        
        self.db_session.add(integration)
        self.db_session.commit()
        self.db_session.refresh(integration)
        
        return integration

    def update_integration(
        self,
        integration_id: int,
        credentials: Optional[dict] = None,
        config: Optional[dict] = None,
        status: Optional[FinanceIntegrationStatus] = None,
        updated_by_user_id: Optional[int] = None,
    ) -> Optional[FinanceIntegration]:
        """Update a finance integration.
        
        Args:
            integration_id: The integration ID.
            credentials: Optional new credentials (will be encrypted).
            config: Optional new configuration.
            status: Optional new status.
            updated_by_user_id: ID of the user updating the integration.
            
        Returns:
            The updated FinanceIntegration or None if not found.
        """
        integration = self.get_by_id(integration_id)
        if not integration:
            return None
        
        if credentials is not None:
            integration.encrypted_credentials = encrypt_credentials(credentials)
        
        if config is not None:
            integration.config_json = config
        
        if status is not None:
            integration.status = status
        
        if updated_by_user_id is not None:
            integration.updated_by_user_id = updated_by_user_id
        
        integration.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        self.db_session.refresh(integration)
        
        return integration

    def update_test_result(
        self,
        integration_id: int,
        success: bool,
        error_message: Optional[str] = None,
    ) -> Optional[FinanceIntegration]:
        """Update the test result for an integration.
        
        Args:
            integration_id: The integration ID.
            success: Whether the test was successful.
            error_message: Error message if test failed.
            
        Returns:
            The updated FinanceIntegration or None if not found.
        """
        integration = self.get_by_id(integration_id)
        if not integration:
            return None
        
        integration.last_tested_at = datetime.utcnow()
        integration.last_test_success = success
        integration.last_error = error_message if not success else None
        
        if success:
            integration.status = FinanceIntegrationStatus.configured
        else:
            integration.status = FinanceIntegrationStatus.error
        
        integration.updated_at = datetime.utcnow()
        
        self.db_session.commit()
        self.db_session.refresh(integration)
        
        return integration

    def get_decrypted_credentials(self, integration_id: int) -> Optional[dict]:
        """Get decrypted credentials for an integration.
        
        Args:
            integration_id: The integration ID.
            
        Returns:
            Decrypted credentials dictionary or None.
        """
        integration = self.get_by_id(integration_id)
        if not integration or not integration.encrypted_credentials:
            return None
        
        return decrypt_credentials(integration.encrypted_credentials)

    def delete_integration(self, integration_id: int) -> bool:
        """Delete a finance integration.
        
        Args:
            integration_id: The integration ID.
            
        Returns:
            True if deleted, False if not found.
        """
        integration = self.get_by_id(integration_id)
        if not integration:
            return False
        
        self.db_session.delete(integration)
        self.db_session.commit()
        return True
