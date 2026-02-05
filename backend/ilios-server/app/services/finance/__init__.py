"""Finance provider abstraction module.

This module provides a pluggable architecture for integrating with
external finance systems (Gravity, QuickBooks, etc.) in a read-only manner.
"""

from .provider import FinanceProvider, FinanceProviderError, ConnectionTestResult
from .registry import FinanceProviderRegistry, get_provider_registry
from .gravity_provider import GravityFinanceProvider

__all__ = [
    "FinanceProvider",
    "FinanceProviderError",
    "ConnectionTestResult",
    "FinanceProviderRegistry",
    "get_provider_registry",
    "GravityFinanceProvider",
]
