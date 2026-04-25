"""Value objects exchanged between adapters and the rest of the app."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExternalSiteRecord:
    """A single external site as reported by a provider."""

    external_site_id: str
    external_site_name: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TestResult:
    """Outcome of an adapter ``test_credentials`` call."""

    success: bool
    message: str
    available_sites_count: int | None = None
