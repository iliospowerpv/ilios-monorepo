"""Schemas for Device Inventory Reconciliation reviewer acknowledgements (Phase B).

A reviewer may acknowledge ("sign off on") an ACTIONABLE inventory-reconciliation
mismatch — recording that it has been checked and is an acceptable exception —
without mutating any operational truth (devices/mappings/facts/telemetry/weather/
baselines are never touched). Acknowledgements are bound to the EXACT
``(mismatch_signature, reconciliation_version)`` pair; the server re-derives the
live reconciliation and snapshots the mismatch itself, so the client only
supplies the target signature plus a rationale.

Blocking mismatches (``not_acknowledgeable_blocking``, e.g. the Site-4 weather
dependency) can never be acknowledged — the service rejects such requests.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

_MIN_REASON_LEN = 10
_MAX_REASON_LEN = 1000


class InventoryAckCreateRequest(BaseModel):
    """Request to acknowledge one actionable mismatch on a site."""

    mismatch_signature: str = Field(min_length=1, max_length=512)
    reconciliation_version: str = Field(min_length=1, max_length=64)
    acknowledgement_reason: str = Field(min_length=1)

    @field_validator("acknowledgement_reason")
    @classmethod
    def _validate_reason(cls, v: str) -> str:
        trimmed = (v or "").strip()
        if len(trimmed) < _MIN_REASON_LEN:
            raise ValueError(
                f"acknowledgement_reason must be at least {_MIN_REASON_LEN} "
                "non-whitespace characters."
            )
        if len(trimmed) > _MAX_REASON_LEN:
            raise ValueError(
                f"acknowledgement_reason must be at most {_MAX_REASON_LEN} characters."
            )
        return trimmed


class InventoryAckRevokeRequest(BaseModel):
    """Request to revoke an existing acknowledgement."""

    revocation_reason: str = Field(min_length=1)

    @field_validator("revocation_reason")
    @classmethod
    def _validate_reason(cls, v: str) -> str:
        trimmed = (v or "").strip()
        if len(trimmed) < _MIN_REASON_LEN:
            raise ValueError(
                f"revocation_reason must be at least {_MIN_REASON_LEN} "
                "non-whitespace characters."
            )
        if len(trimmed) > _MAX_REASON_LEN:
            raise ValueError(
                f"revocation_reason must be at most {_MAX_REASON_LEN} characters."
            )
        return trimmed


class InventoryAckResponse(BaseModel):
    """One acknowledgement row (with a read-time derived ``is_active`` flag)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    mismatch_signature: str
    reconciliation_version: str

    mismatch_type: str
    severity: str
    acknowledgement_policy: str
    mismatch_title: str
    mismatch_detail: Optional[str] = None
    source_module: Optional[str] = None
    acknowledged_context_hash: Optional[str] = None

    status: str
    acknowledged_by: Optional[int] = None
    acknowledged_at: datetime
    acknowledgement_reason: str
    revoked_by: Optional[int] = None
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Derived at read time (DB enum stays {acknowledged, revoked}): an ack is
    # "active" only while status==acknowledged AND its reconciliation_version still
    # matches the current engine version. A stale-version ack reads as inactive
    # ("expired") even though it is persisted as acknowledged.
    is_active: bool = False
    is_expired: bool = False


class InventoryAckListResponse(BaseModel):
    """All acknowledgement rows for a site (most-recent first)."""

    site_id: int
    reconciliation_version: str
    acknowledgements: list[InventoryAckResponse] = Field(default_factory=list)
