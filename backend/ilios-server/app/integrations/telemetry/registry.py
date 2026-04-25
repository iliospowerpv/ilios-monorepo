"""Resolve catalog rows to concrete adapter instances."""
from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Optional

from sqlalchemy.orm import Session

from app.models.telemetry import TelemetryProviderCatalog

from .base import ProviderAdapter, ProviderError


class _AdapterFactoryError(ProviderError):
    """Raised when the catalog row references an unknown / invalid adapter class."""


@lru_cache(maxsize=64)
def _load_adapter_class(dotted_path: str) -> type:
    module_path, _, class_name = dotted_path.rpartition(".")
    if not module_path or not class_name:
        raise _AdapterFactoryError(f"Invalid adapter path: {dotted_path!r}")
    module = importlib.import_module(module_path)
    try:
        return getattr(module, class_name)
    except AttributeError as exc:  # pragma: no cover - guarded
        raise _AdapterFactoryError(
            f"Adapter class {class_name!r} not found in {module_path!r}"
        ) from exc


def clear_registry_cache() -> None:
    _load_adapter_class.cache_clear()


def get_adapter(
    db_session: Session,
    provider_key: str,
    *,
    catalog: Optional[TelemetryProviderCatalog] = None,
) -> ProviderAdapter:
    """Return an adapter instance for ``provider_key``.

    The catalog row may be passed in to avoid an extra DB lookup when the
    caller already has it (e.g. inside a transaction touching the row).
    """
    if catalog is None:
        catalog = (
            db_session.query(TelemetryProviderCatalog)
            .filter(TelemetryProviderCatalog.provider_key == provider_key)
            .first()
        )
    if catalog is None or not catalog.is_enabled:
        raise _AdapterFactoryError(
            f"Provider {provider_key!r} is not registered or is disabled"
        )
    cls = _load_adapter_class(catalog.adapter_class)
    instance = cls()
    if not isinstance(instance, ProviderAdapter):
        raise _AdapterFactoryError(
            f"{catalog.adapter_class!r} does not implement ProviderAdapter"
        )
    return instance
