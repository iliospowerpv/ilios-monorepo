"""Resolve weather provider catalog rows to concrete adapter instances.

Mirrors ``app/integrations/telemetry/registry.py``: a catalog ``adapter_class``
dotted path is imported and instantiated, then validated against the
:class:`WeatherProviderAdapter` Protocol. Disabled/unknown providers are
refused so a dark provider can never be invoked.
"""
from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Optional

from sqlalchemy.orm import Session

from app.models.weather import WeatherProviderCatalog

from .base import WeatherProviderAdapter, WeatherProviderError


class _WeatherAdapterFactoryError(WeatherProviderError):
    """Raised when the catalog row references an unknown / invalid adapter class."""


@lru_cache(maxsize=64)
def _load_adapter_class(dotted_path: str) -> type:
    module_path, _, class_name = dotted_path.rpartition(".")
    if not module_path or not class_name:
        raise _WeatherAdapterFactoryError(f"Invalid adapter path: {dotted_path!r}")
    module = importlib.import_module(module_path)
    try:
        return getattr(module, class_name)
    except AttributeError as exc:  # pragma: no cover - guarded
        raise _WeatherAdapterFactoryError(
            f"Adapter class {class_name!r} not found in {module_path!r}"
        ) from exc


def clear_registry_cache() -> None:
    _load_adapter_class.cache_clear()


def get_weather_adapter(
    db_session: Session,
    provider_key: str,
    *,
    catalog: Optional[WeatherProviderCatalog] = None,
) -> WeatherProviderAdapter:
    """Return an adapter instance for ``provider_key``.

    The catalog row may be passed in to avoid an extra DB lookup when the caller
    already holds it. Unknown or disabled providers raise.
    """
    if catalog is None:
        catalog = (
            db_session.query(WeatherProviderCatalog)
            .filter(WeatherProviderCatalog.provider_key == provider_key)
            .first()
        )
    if catalog is None or not catalog.is_enabled:
        raise _WeatherAdapterFactoryError(
            f"Weather provider {provider_key!r} is not registered or is disabled"
        )
    cls = _load_adapter_class(catalog.adapter_class)
    instance = cls()
    if not isinstance(instance, WeatherProviderAdapter):
        raise _WeatherAdapterFactoryError(
            f"{catalog.adapter_class!r} does not implement WeatherProviderAdapter"
        )
    return instance
