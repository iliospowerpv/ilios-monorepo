"""Shared telemetry audit-log helper.

Extracted from the legacy ``telemetry`` router so the V2 router (``v2.py``) no
longer imports from the legacy module. Behavior is unchanged: a best-effort
audit row that never raises.
"""
import json
import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.crud.audit_log import AuditLogCRUD

logger = logging.getLogger(__name__)

# Source tag for expected-baseline lifecycle audit events (Phase B3 Tier 1).
# Distinct from the generic ``"telemetry"`` source so baseline lifecycle events
# can be filtered cleanly without touching the existing telemetry audit stream.
BASELINE_AUDIT_SOURCE = "telemetry_baseline"


def create_audit_log(
    request: Request, db_session: Session, action: str, details: str, is_success: bool = True
):
    """Create an audit log entry for telemetry operations (best-effort)."""
    try:
        user_id = getattr(request.state, "current_user_id", None)
        AuditLogCRUD(db_session).create_item({
            "source": "telemetry",
            "action": action,
            "details": details,
            "is_success": is_success,
            "user_id": user_id,
        })
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")


def create_baseline_audit_log(
    db_session: Session,
    *,
    user_id: Optional[int],
    action: str,
    details: dict,
    is_success: bool = True,
) -> None:
    """Best-effort audit row for an expected-baseline lifecycle action.

    Phase B3 Tier 1. This is deliberately isolated from the baseline lifecycle
    transaction: callers invoke it AFTER the lifecycle CRUD has already committed
    (success) or AFTER a fail-closed block that performed NO mutation. The row is
    committed by ``AuditLogCRUD.create_item``; ``details`` is JSON-encoded into the
    existing VARCHAR ``audit_logs.details`` column (no migration). On ANY failure
    it rolls back its own pending write and logs a warning — it NEVER raises, so an
    audit failure can never block, roll back, or alter approve/activate behavior.
    """
    try:
        AuditLogCRUD(db_session).create_item({
            "source": BASELINE_AUDIT_SOURCE,
            "action": action,
            "details": json.dumps(details, default=str, sort_keys=True),
            "is_success": is_success,
            "user_id": user_id,
        })
    except Exception as e:  # best-effort: never propagate to the lifecycle path
        logger.warning("Failed to create baseline audit log (action=%s): %s", action, e)
        try:
            db_session.rollback()
        except Exception:  # pragma: no cover - defensive cleanup
            pass
