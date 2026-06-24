"""Governed write path for Device Inventory Reconciliation acknowledgements (Phase B).

A reviewer may acknowledge ("sign off on") an ACTIONABLE inventory-reconciliation
mismatch, recording that it has been checked and is an acceptable exception. This
is the ONLY write path Phase B introduces and it is strictly additive: it writes
exclusively to ``inventory_mismatch_acknowledgements`` and NEVER mutates
``devices``, ``telemetry_*`` mappings, ``project_facts``, ``weather_device_mappings``,
or baselines.

Hard guarantees enforced here:

* **Server re-derives the truth.** The live reconciliation is recomputed and the
  acknowledged mismatch is matched by its EXACT ``mismatch_signature`` AND the
  current ``reconciliation_version``. The client's claimed version must equal the
  current engine version, so a stale client can never acknowledge against a
  superseded rule set. The persisted snapshot is taken from the server-derived
  mismatch, not from client input.
* **Blocking can never be acknowledged.** A ``not_acknowledgeable_blocking``
  mismatch (e.g. the Site-4 weather dependency) is rejected with 422; informational
  findings are likewise not acknowledgeable. Only ``acknowledgeable_*`` policies
  may be signed off.
* **One active ack per (site, signature, version).** A second acknowledge while
  one is active is a 409; a revoke retains the row as history and a later
  acknowledge creates a fresh row.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.helpers.telemetry.audit import create_audit_log as _create_audit_log
from app.models.inventory_acknowledgement import (
    InventoryAckStatus,
    InventoryMismatchAcknowledgement,
)
from app.models.site import Site
from app.schema.inventory_acknowledgement import (
    InventoryAckCreateRequest,
    InventoryAckListResponse,
    InventoryAckResponse,
    InventoryAckRevokeRequest,
)
from app.schema.inventory_reconciliation import InventoryAckPolicy, InventoryMismatch
from app.services.telemetry import device_inventory_reconciliation_service as recon_svc

logger = logging.getLogger(__name__)

_ACKNOWLEDGEABLE_POLICIES = (
    InventoryAckPolicy.acknowledgeable_with_required_followup,
    InventoryAckPolicy.acknowledgeable_non_blocking,
)


# ---------------------------------------------------------------------------
# Read-time projection helpers
# ---------------------------------------------------------------------------
def _to_response(ack: InventoryMismatchAcknowledgement) -> InventoryAckResponse:
    """Project an ack row to its API shape with the derived active/expired flags.

    The DB enum stays ``{acknowledged, revoked}``; "expired" is derived at read
    time: an acknowledged row whose ``reconciliation_version`` no longer matches
    the current engine version is inert (``is_active=False``, ``is_expired=True``)
    even though it is still persisted as ``acknowledged``.
    """
    resp = InventoryAckResponse.model_validate(ack)
    is_acknowledged = ack.status == InventoryAckStatus.acknowledged
    version_current = (
        ack.reconciliation_version == recon_svc.RECONCILIATION_VERSION
    )
    resp.is_active = is_acknowledged and version_current
    resp.is_expired = is_acknowledged and not version_current
    return resp


def _context_hash(mismatch: InventoryMismatch) -> str:
    """Stable fingerprint of the acknowledged mismatch's identity + key context.

    Lets a future consumer detect that the underlying finding's salient context
    drifted even when the signature is unchanged. Purely descriptive; never used
    for matching (matching is signature + version only).
    """
    parts = [
        mismatch.mismatch_signature,
        mismatch.category.value,
        mismatch.acknowledgement_policy.value,
        mismatch.blocking_level.value,
        str(mismatch.device_id or ""),
        mismatch.external_device_id or "",
        mismatch.documented_value or "",
        mismatch.observed_value or "",
    ]
    return hashlib.sha256("\u0001".join(parts).encode("utf-8")).hexdigest()


def _source_context(mismatch: InventoryMismatch) -> dict:
    """Minimal descriptive snapshot of the mismatch's locators (never matched on)."""
    ctx: dict = {
        "category": mismatch.category.value,
        "blocking_level": mismatch.blocking_level.value,
    }
    if mismatch.equipment_class is not None:
        ctx["equipment_class"] = mismatch.equipment_class.value
    if mismatch.device_id is not None:
        ctx["device_id"] = mismatch.device_id
    if mismatch.device_name:
        ctx["device_name"] = mismatch.device_name
    if mismatch.external_device_id:
        ctx["external_device_id"] = mismatch.external_device_id
    return ctx


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def create_acknowledgement(
    db: Session,
    *,
    site: Site,
    payload: InventoryAckCreateRequest,
    user_id: Optional[int],
    request: Optional[Request] = None,
) -> InventoryAckResponse:
    """Acknowledge one actionable mismatch after re-deriving the live truth.

    Raises ``HTTPException`` 409/404/422 for stale version, unknown signature, or a
    non-acknowledgeable (blocking/informational) target respectively; 409 again if
    an active acknowledgement already exists for the triple.
    """
    # 1. Re-derive the live reconciliation (read-only) and pin the version.
    recon = recon_svc.build_site_inventory_reconciliation(db, site)
    if payload.reconciliation_version != recon.reconciliation_version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Reconciliation has changed since this view was loaded "
            f"(expected version {recon.reconciliation_version!r}, "
            f"got {payload.reconciliation_version!r}). Reload and try again.",
        )

    # 2. Locate the exact mismatch the reviewer intends to acknowledge.
    mismatch = next(
        (
            m
            for m in recon.mismatches
            if m.mismatch_signature == payload.mismatch_signature
        ),
        None,
    )
    if mismatch is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No current mismatch matches that signature; it may have been resolved "
            "or never existed. Reload the reconciliation.",
        )

    # 3. Only actionable (acknowledgeable) findings may be signed off. Blocking
    #    findings can NEVER be acknowledged away.
    if mismatch.acknowledgement_policy == InventoryAckPolicy.not_acknowledgeable_blocking:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This is a blocking mismatch and cannot be acknowledged. It must be "
            "resolved at its source.",
        )
    if mismatch.acknowledgement_policy not in _ACKNOWLEDGEABLE_POLICIES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This mismatch is informational and does not require acknowledgement.",
        )

    # 4. Enforce one active acknowledgement per (site, signature, version).
    existing = (
        db.query(InventoryMismatchAcknowledgement)
        .filter(
            InventoryMismatchAcknowledgement.site_id == site.id,
            InventoryMismatchAcknowledgement.mismatch_signature
            == payload.mismatch_signature,
            InventoryMismatchAcknowledgement.reconciliation_version
            == recon.reconciliation_version,
            InventoryMismatchAcknowledgement.status
            == InventoryAckStatus.acknowledged,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This mismatch is already acknowledged.",
        )

    # 5. Persist the acknowledgement, snapshotting the SERVER-derived mismatch.
    ack = InventoryMismatchAcknowledgement(
        site_id=site.id,
        mismatch_signature=mismatch.mismatch_signature,
        reconciliation_version=recon.reconciliation_version,
        mismatch_type=mismatch.category.value,
        severity=mismatch.blocking_level.value,
        acknowledgement_policy=mismatch.acknowledgement_policy.value,
        mismatch_title=mismatch.title,
        mismatch_detail=mismatch.detail,
        source_module=recon_svc.SOURCE_MODULE,
        source_context=_source_context(mismatch),
        acknowledged_context_hash=_context_hash(mismatch),
        status=InventoryAckStatus.acknowledged,
        acknowledged_by=user_id,
        acknowledged_at=datetime.utcnow(),
        acknowledgement_reason=payload.acknowledgement_reason,
    )
    db.add(ack)
    db.commit()
    db.refresh(ack)

    if request is not None:
        _create_audit_log(
            request,
            db,
            "inventory_reconciliation.acknowledge",
            f"site={site.id} signature={mismatch.mismatch_signature!r} "
            f"version={recon.reconciliation_version!r} ack_id={ack.id}",
        )

    return _to_response(ack)


# ---------------------------------------------------------------------------
# Revoke
# ---------------------------------------------------------------------------
def revoke_acknowledgement(
    db: Session,
    *,
    site: Site,
    ack_id: int,
    payload: InventoryAckRevokeRequest,
    user_id: Optional[int],
    request: Optional[Request] = None,
) -> InventoryAckResponse:
    """Revoke an active acknowledgement (retained as immutable history)."""
    ack = (
        db.query(InventoryMismatchAcknowledgement)
        .filter(
            InventoryMismatchAcknowledgement.id == ack_id,
            InventoryMismatchAcknowledgement.site_id == site.id,
        )
        .one_or_none()
    )
    if ack is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Acknowledgement not found for this site."
        )
    if ack.status != InventoryAckStatus.acknowledged:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Acknowledgement is already revoked."
        )

    ack.status = InventoryAckStatus.revoked
    ack.revoked_by = user_id
    ack.revoked_at = datetime.utcnow()
    ack.revocation_reason = payload.revocation_reason
    db.add(ack)
    db.commit()
    db.refresh(ack)

    if request is not None:
        _create_audit_log(
            request,
            db,
            "inventory_reconciliation.revoke_acknowledgement",
            f"site={site.id} ack_id={ack.id} signature={ack.mismatch_signature!r}",
        )

    return _to_response(ack)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
def list_acknowledgements(
    db: Session, *, site: Site
) -> InventoryAckListResponse:
    """Return every acknowledgement row for the site (most-recent first).

    Read-only. Each row carries the derived ``is_active`` / ``is_expired`` flags
    relative to the current engine version.
    """
    rows = (
        db.query(InventoryMismatchAcknowledgement)
        .filter(InventoryMismatchAcknowledgement.site_id == site.id)
        .order_by(InventoryMismatchAcknowledgement.created_at.desc())
        .all()
    )
    return InventoryAckListResponse(
        site_id=site.id,
        reconciliation_version=recon_svc.RECONCILIATION_VERSION,
        acknowledgements=[_to_response(r) for r in rows],
    )
