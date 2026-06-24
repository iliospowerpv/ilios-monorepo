"""Reviewer acknowledgements for Device Inventory Reconciliation mismatches.

Phase B adds the FIRST governed write path for Device Inventory Reconciliation.
A reviewer may record "I checked this mismatch and it is an acceptable exception"
WITHOUT mutating any operational truth. This table is strictly additive: it never
changes ``devices``, ``telemetry_devices_mapping`` / ``telemetry_sites_mapping``,
``project_facts``, ``telemetry_*``, ``weather_device_mappings``, or baselines.

An acknowledgement is bound to an EXACT ``(site_id, mismatch_signature,
reconciliation_version)`` triple. If a future reconciliation rule change alters
the signature OR the engine version, the old acknowledgement no longer applies
(it becomes inert / "expired" at read time) — it is never silently reused.

Rows are append-on-acknowledge; a revoke flips ``status`` -> ``revoked`` and
stamps ``revoked_by`` / ``revoked_at`` / ``revocation_reason`` (the row is never
deleted, preserving the audit trail). The mismatch details are SNAPSHOTTED at
acknowledgement time so the trail stays meaningful even if the live mismatch
later changes or disappears.

Blocking mismatches (``not_acknowledgeable_blocking``, e.g. the Site-4 weather
dependency) can never be acknowledged — that gate is enforced in the service, and
the ladder keeps such a site at ``needs_reconciliation`` regardless of any row
that might exist here.
"""
import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class InventoryAckStatus(str, enum.Enum):
    """Persisted lifecycle of an acknowledgement row.

    Only two states are persisted. The derived "expired" state (the live mismatch
    signature / reconciliation version no longer matches) is computed at READ time
    so the reconciliation read path stays strictly zero-mutation.
    """

    acknowledged = "acknowledged"
    revoked = "revoked"


# Postgres enum type name (kept in lockstep with the migration constant).
INVENTORY_ACK_STATUS_ENUM_NAME = "inventory_ack_status_enum"
_ACK_STATUS_ENUM = Enum(InventoryAckStatus, name=INVENTORY_ACK_STATUS_ENUM_NAME)


class InventoryMismatchAcknowledgement(Base):
    """One reviewer acknowledgement of a specific inventory-reconciliation mismatch.

    Bound to an exact ``(site_id, mismatch_signature, reconciliation_version)``
    triple. At most one ``acknowledged`` row may exist per triple (enforced by a
    partial unique index); revoked rows are retained as history and a fresh
    acknowledgement after a revoke creates a new row.
    """

    __tablename__ = "inventory_mismatch_acknowledgements"
    __table_args__ = (
        Index(
            "ix_inv_mismatch_ack_site_status",
            "site_id",
            "status",
        ),
        Index(
            "ix_inv_mismatch_ack_signature",
            "site_id",
            "mismatch_signature",
            "reconciliation_version",
        ),
        Index(
            "uq_inv_mismatch_ack_active",
            "site_id",
            "mismatch_signature",
            "reconciliation_version",
            unique=True,
            postgresql_where=text("status = 'acknowledged'"),
        ),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(
        Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False
    )

    # --- Identity of the acknowledged mismatch (exact-match key) -------------
    mismatch_signature = Column(String(512), nullable=False)
    reconciliation_version = Column(String(64), nullable=False)

    # --- Snapshot of the mismatch at acknowledgement time -------------------
    mismatch_type = Column(String(128), nullable=False)
    severity = Column(String(64), nullable=False)
    acknowledgement_policy = Column(String(64), nullable=False)
    mismatch_title = Column(Text, nullable=False)
    mismatch_detail = Column(Text, nullable=True)
    source_module = Column(String(128), nullable=True)
    source_context = Column(JSONB, nullable=True)
    acknowledged_context_hash = Column(String(64), nullable=True)

    # --- Acknowledgement audit ---------------------------------------------
    status = Column(
        _ACK_STATUS_ENUM,
        nullable=False,
        server_default=text(f"'acknowledged'::{INVENTORY_ACK_STATUS_ENUM_NAME}"),
    )
    acknowledged_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    acknowledged_at = Column(DateTime, nullable=False, server_default=utcnow())
    acknowledgement_reason = Column(Text, nullable=False)

    # --- Revocation audit (null until revoked) ------------------------------
    revoked_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at = Column(DateTime, nullable=True)
    revocation_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, server_default=utcnow())
    updated_at = Column(
        DateTime, nullable=False, server_default=utcnow(), onupdate=utcnow()
    )

    acknowledged_by_user = relationship(
        "User", foreign_keys=[acknowledged_by], viewonly=True
    )
    revoked_by_user = relationship("User", foreign_keys=[revoked_by], viewonly=True)

    def __repr__(self) -> str:
        return (
            f"<InventoryMismatchAcknowledgement(id={self.id}, site={self.site_id}, "
            f"sig={self.mismatch_signature!r}, ver={self.reconciliation_version!r}, "
            f"status={self.status})>"
        )
