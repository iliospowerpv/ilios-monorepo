"""Gravity Finance Provider implementation.

Provides both a production path (fails gracefully when real API unavailable)
and a deterministic stub path (behind config flag) for dev/test environments.

Stub gating rule: config_json must contain {"use_stub_data": true}.
In production/staging the flag is absent, so fetch_* raises a clear
'provider_not_implemented' error if real API integration is not yet wired.
"""

from datetime import datetime, date
from typing import Optional
import logging
import os

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

STUB_ACCOUNTS = [
    FinanceAccount(
        id="GRAV-ACCT-001",
        name="Operating Account",
        account_type="checking",
        balance=125000.00,
        currency="USD",
        is_active=True,
        metadata={"gravity_entity": "main_ops"},
    ),
    FinanceAccount(
        id="GRAV-ACCT-002",
        name="Reserve Fund",
        account_type="savings",
        balance=500000.00,
        currency="USD",
        is_active=True,
        metadata={"gravity_entity": "reserve"},
    ),
    FinanceAccount(
        id="GRAV-ACCT-003",
        name="Capital Improvements",
        account_type="checking",
        balance=75000.00,
        currency="USD",
        is_active=True,
        metadata={"gravity_entity": "capex"},
    ),
]

STUB_TRANSACTIONS = [
    FinanceTransaction(
        id="GRAV-TXN-001",
        account_id="GRAV-ACCT-001",
        date=datetime(2026, 1, 15),
        amount=-4500.00,
        description="Property Management Fee - January",
        category="management_fee",
        reference="PropMgmt Inc.",
        metadata={"gravity_batch": "B2026-01"},
    ),
    FinanceTransaction(
        id="GRAV-TXN-002",
        account_id="GRAV-ACCT-001",
        date=datetime(2026, 1, 20),
        amount=18500.00,
        description="Rent Collection - Unit Block A",
        category="rental_income",
        reference="Tenants Block A",
        metadata={"gravity_batch": "B2026-01"},
    ),
    FinanceTransaction(
        id="GRAV-TXN-003",
        account_id="GRAV-ACCT-003",
        date=datetime(2026, 1, 25),
        amount=-12000.00,
        description="HVAC Replacement - Building 2",
        category="capital_expense",
        reference="ClimateControl LLC",
        metadata={"gravity_batch": "B2026-01"},
    ),
    FinanceTransaction(
        id="GRAV-TXN-004",
        account_id="GRAV-ACCT-001",
        date=datetime(2026, 2, 1),
        amount=-2200.00,
        description="Insurance Premium - Q1",
        category="insurance",
        reference="SafeGuard Insurance",
        metadata={"gravity_batch": "B2026-02"},
    ),
    FinanceTransaction(
        id="GRAV-TXN-005",
        account_id="GRAV-ACCT-002",
        date=datetime(2026, 2, 3),
        amount=1250.00,
        description="Interest Earned - January",
        category="interest_income",
        reference="First National Bank",
        metadata={"gravity_batch": "B2026-02"},
    ),
]


class GravityFinanceProvider(FinanceProvider):
    """Finance provider for Gravity financial system.

    Production path: raises 'provider_not_implemented' when real API
    integration is not yet wired.

    Stub path: returns deterministic test data when config contains
    {"use_stub_data": true}. Blocked in production unless explicitly
    force-allowed via FINANCE_ALLOW_STUB_IN_PROD env var.
    """

    def __init__(self, credentials: dict, config: Optional[dict] = None):
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

    @property
    def _use_stub(self) -> bool:
        """Whether to return stub data instead of hitting real API."""
        flag = self._config.get("use_stub_data", False)
        if not flag:
            return False
        env = os.environ.get("REPLIT_DEPLOYMENT", "").lower()
        if env in ("production", "staging"):
            force = os.environ.get("FINANCE_ALLOW_STUB_IN_PROD", "").lower()
            if force != "true":
                logger.warning(
                    "Stub data requested in %s but FINANCE_ALLOW_STUB_IN_PROD is not set",
                    env,
                )
                return False
        return True

    def test_connection(self) -> ConnectionTestResult:
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
                "stub_mode": self._use_stub,
            },
        )

    def fetch_accounts(self) -> list[FinanceAccount]:
        if self._use_stub:
            logger.info("Fetching accounts from Gravity (stub data)")
            return list(STUB_ACCOUNTS)

        logger.warning("Gravity real API not implemented; returning error")
        raise FinanceProviderError(
            message="Gravity API integration not yet implemented. "
                    "Enable stub data via config {\"use_stub_data\": true} for dev/test.",
            provider_key=self.provider_key,
            error_code="PROVIDER_NOT_IMPLEMENTED",
        )

    def fetch_transactions(
        self,
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[FinanceTransaction]:
        if self._use_stub:
            logger.info("Fetching transactions from Gravity (stub data)")
            txns = list(STUB_TRANSACTIONS)
            if account_id:
                txns = [t for t in txns if t.account_id == account_id]
            if start_date:
                txns = [t for t in txns if t.date >= start_date]
            if end_date:
                txns = [t for t in txns if t.date <= end_date]
            return txns

        logger.warning("Gravity real API not implemented; returning error")
        raise FinanceProviderError(
            message="Gravity API integration not yet implemented. "
                    "Enable stub data via config {\"use_stub_data\": true} for dev/test.",
            provider_key=self.provider_key,
            error_code="PROVIDER_NOT_IMPLEMENTED",
        )

    def fetch_budgets(self) -> list[FinanceBudget]:
        if self._use_stub:
            logger.info("Fetching budgets from Gravity (stub data)")
            return []

        logger.warning("Gravity real API not implemented; returning error")
        raise FinanceProviderError(
            message="Gravity API integration not yet implemented.",
            provider_key=self.provider_key,
            error_code="PROVIDER_NOT_IMPLEMENTED",
        )
