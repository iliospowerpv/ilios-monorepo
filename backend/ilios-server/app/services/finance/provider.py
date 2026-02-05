"""Finance provider interface definition.

Defines the abstract interface for all finance system integrations.
All providers must implement these methods for read-only data access.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class FinanceProviderError(Exception):
    """Base exception for finance provider errors."""
    
    def __init__(self, message: str, provider_key: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.provider_key = provider_key
        self.error_code = error_code


class ConnectionStatus(str, Enum):
    """Connection test result status."""
    SUCCESS = "success"
    FAILURE = "failure"
    INVALID_CREDENTIALS = "invalid_credentials"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"


@dataclass
class ConnectionTestResult:
    """Result of a connection test."""
    success: bool
    status: ConnectionStatus
    message: str
    tested_at: datetime = field(default_factory=datetime.utcnow)
    details: Optional[dict] = None


@dataclass
class FinanceAccount:
    """Represents a financial account from the provider."""
    id: str
    name: str
    account_type: str
    balance: Optional[float] = None
    currency: str = "USD"
    is_active: bool = True
    metadata: Optional[dict] = None


@dataclass
class FinanceTransaction:
    """Represents a financial transaction from the provider."""
    id: str
    account_id: str
    date: datetime
    amount: float
    description: str
    category: Optional[str] = None
    reference: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class FinanceBudget:
    """Represents a budget from the provider."""
    id: str
    name: str
    period_start: datetime
    period_end: datetime
    total_amount: float
    spent_amount: float = 0.0
    remaining_amount: float = 0.0
    categories: Optional[dict] = None
    metadata: Optional[dict] = None


class FinanceProvider(ABC):
    """Abstract base class for finance system providers.
    
    All finance providers must implement this interface to ensure
    consistent behavior across different systems (Gravity, QuickBooks, etc.).
    
    This is a READ-ONLY interface - no write operations are supported.
    """
    
    @property
    @abstractmethod
    def provider_key(self) -> str:
        """Unique identifier for this provider (e.g., 'gravity', 'quickbooks')."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the provider."""
        pass
    
    @property
    @abstractmethod
    def supports_budgets(self) -> bool:
        """Whether this provider supports budget data."""
        pass
    
    @abstractmethod
    def test_connection(self) -> ConnectionTestResult:
        """Test the connection to the finance system.
        
        Returns:
            ConnectionTestResult with success status and details.
        """
        pass
    
    @abstractmethod
    def fetch_accounts(self) -> list[FinanceAccount]:
        """Fetch all accounts from the finance system.
        
        Returns:
            List of FinanceAccount objects.
            
        Raises:
            FinanceProviderError: If the fetch fails.
        """
        pass
    
    @abstractmethod
    def fetch_transactions(
        self,
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[FinanceTransaction]:
        """Fetch transactions from the finance system.
        
        Args:
            account_id: Optional filter by account ID.
            start_date: Optional filter by start date.
            end_date: Optional filter by end date.
            
        Returns:
            List of FinanceTransaction objects.
            
        Raises:
            FinanceProviderError: If the fetch fails.
        """
        pass
    
    def fetch_budgets(self) -> list[FinanceBudget]:
        """Fetch budgets from the finance system.
        
        Optional method - default implementation returns empty list.
        Override this method if the provider supports budgets.
        
        Returns:
            List of FinanceBudget objects.
            
        Raises:
            FinanceProviderError: If the fetch fails.
        """
        if not self.supports_budgets:
            return []
        raise NotImplementedError("Provider claims to support budgets but fetch_budgets not implemented")
