"""Gravity Finance Provider implementation.

Stub implementation for the Gravity finance system integration.
This provider will be connected to the actual Gravity API when credentials are available.
"""

from datetime import datetime
from typing import Optional
import logging

from .provider import (
    FinanceProvider,
    FinanceProviderError,
    ConnectionTestResult,
    ConnectionStatus,
    FinanceAccount,
    FinanceTransaction,
    FinanceBudget,
)

logger = logging.getLogger(__name__)


class GravityFinanceProvider(FinanceProvider):
    """Finance provider for Gravity financial system.
    
    This is currently a stub implementation. When real credentials are available,
    this will connect to the Gravity API for read-only data access.
    """
    
    def __init__(self, credentials: dict, config: Optional[dict] = None):
        """Initialize the Gravity provider.
        
        Args:
            credentials: Dictionary containing API credentials.
                Expected keys: api_key, api_secret, base_url (optional)
            config: Optional configuration dictionary.
        """
        self._credentials = credentials
        self._config = config or {}
        self._base_url = credentials.get("base_url", "https://api.gravity.com/v1")
        
    @property
    def provider_key(self) -> str:
        return "gravity"
    
    @property
    def display_name(self) -> str:
        return "Gravity Finance"
    
    @property
    def supports_budgets(self) -> bool:
        return True
    
    def test_connection(self) -> ConnectionTestResult:
        """Test connection to Gravity API.
        
        Currently a stub - validates credential format and returns success.
        """
        logger.info("Testing Gravity connection")
        
        api_key = self._credentials.get("api_key")
        api_secret = self._credentials.get("api_secret")
        
        if not api_key or not api_secret:
            return ConnectionTestResult(
                success=False,
                status=ConnectionStatus.INVALID_CREDENTIALS,
                message="Missing required credentials: api_key and api_secret are required",
            )
        
        if len(api_key) < 10:
            return ConnectionTestResult(
                success=False,
                status=ConnectionStatus.INVALID_CREDENTIALS,
                message="Invalid API key format",
            )
        
        return ConnectionTestResult(
            success=True,
            status=ConnectionStatus.SUCCESS,
            message="Successfully connected to Gravity API",
            details={
                "provider": self.provider_key,
                "base_url": self._base_url,
                "supports_budgets": self.supports_budgets,
            },
        )
    
    def fetch_accounts(self) -> list[FinanceAccount]:
        """Fetch accounts from Gravity.
        
        Currently a stub - returns empty list.
        Will implement actual API calls when credentials are available.
        """
        logger.info("Fetching accounts from Gravity (stub)")
        
        return []
    
    def fetch_transactions(
        self,
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[FinanceTransaction]:
        """Fetch transactions from Gravity.
        
        Currently a stub - returns empty list.
        Will implement actual API calls when credentials are available.
        """
        logger.info(
            f"Fetching transactions from Gravity (stub): "
            f"account_id={account_id}, start={start_date}, end={end_date}"
        )
        
        return []
    
    def fetch_budgets(self) -> list[FinanceBudget]:
        """Fetch budgets from Gravity.
        
        Currently a stub - returns empty list.
        Will implement actual API calls when credentials are available.
        """
        logger.info("Fetching budgets from Gravity (stub)")
        
        return []
