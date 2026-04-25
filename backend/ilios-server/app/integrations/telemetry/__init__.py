"""Telemetry provider integrations (v2).

This package owns all third-party telemetry vendor logic. Routers and
services depend on the abstract :class:`ProviderAdapter` Protocol from
``base`` and obtain concrete adapters from :func:`registry.get_adapter`.
"""
from .base import (
    CredentialError,
    MappingError,
    NoData,
    ProviderAdapter,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
)
from .models import ExternalSiteRecord, TestResult
from .registry import clear_registry_cache, get_adapter

__all__ = [
    "CredentialError",
    "MappingError",
    "NoData",
    "ProviderAdapter",
    "ProviderError",
    "ProviderUnavailable",
    "RateLimited",
    "ExternalSiteRecord",
    "TestResult",
    "clear_registry_cache",
    "get_adapter",
]
