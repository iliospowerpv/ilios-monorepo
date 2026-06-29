"""Best-effort audit helper for the Workflow Engine.

Writes rows with source ``workflow_engine`` (or ``workflow_engine_governed`` for the
hard-prohibited set) so engine activity is filterable alongside existing audit streams
(``telemetry_baseline``, sales transitions, etc.). The domain endpoints the engine invokes
keep their OWN audit; this row links the run/step to the resulting entity for end-to-end
traceability. Like the other audit helpers, it NEVER raises.
"""
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.audit_log import AuditLogCRUD

logger = logging.getLogger(__name__)

WORKFLOW_AUDIT_SOURCE = "workflow_engine"
WORKFLOW_GOVERNED_AUDIT_SOURCE = "workflow_engine_governed"


def create_workflow_audit_log(
    db_session: Session,
    *,
    user_id: Optional[int],
    action: str,
    details: dict,
    is_success: bool = True,
    governed: bool = False,
) -> Optional[int]:
    """Create a workflow audit row; returns its id (or None on failure). Never raises.

    ``details`` is JSON-encoded into the existing VARCHAR ``audit_logs.details`` column (no
    migration). On any failure it rolls back its own pending write and logs a warning, so an
    audit failure can never block or alter engine behavior.
    """
    try:
        row = AuditLogCRUD(db_session).create_item(
            {
                "source": WORKFLOW_GOVERNED_AUDIT_SOURCE if governed else WORKFLOW_AUDIT_SOURCE,
                "action": action,
                "details": json.dumps(details, default=str, sort_keys=True),
                "is_success": is_success,
                "user_id": user_id,
            }
        )
        return getattr(row, "id", None)
    except Exception as e:  # best-effort: never propagate
        logger.warning("Failed to create workflow audit log (action=%s): %s", action, e)
        try:
            db_session.rollback()
        except Exception:  # pragma: no cover - defensive cleanup
            pass
        return None
