"""Telemetry provider integrations (v2).

This package owns all third-party telemetry vendor logic. Routers and
services depend on the abstract :class:`ProviderAdapter` Protocol from
``base`` and obtain concrete adapters from :func:`registry.get_adapter`.
"""
from .base import (
    CredentialError,
    DeviceListingAdapter,
    MappingError,
    NoData,
    ProviderAdapter,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
    ReadingsAdapter,
)
from .models import (
    ExternalDeviceRecord,
    ExternalSiteRecord,
    MetricFieldSpec,
    ReadingRecord,
    ReadingsPullResult,
    TestResult,
)
from .registry import clear_registry_cache, get_adapter

__all__ = [
    "CredentialError",
    "DeviceListingAdapter",
    "MappingError",
    "NoData",
    "ProviderAdapter",
    "ProviderError",
    "ProviderUnavailable",
    "RateLimited",
    "ReadingsAdapter",
    "ExternalDeviceRecord",
    "ExternalSiteRecord",
    "MetricFieldSpec",
    "ReadingRecord",
    "ReadingsPullResult",
    "TestResult",
    "clear_registry_cache",
    "get_adapter",
]
