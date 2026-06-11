"""Shared telemetry audit-log helper.

Extracted from the legacy ``telemetry`` router so the V2 router (``v2.py``) no
longer imports from the legacy module. Behavior is unchanged: a best-effort
audit row that never raises.
"""
import logging

from fastapi import Request
from sqlalchemy.orm import Session

from app.crud.audit_log import AuditLogCRUD

logger = logging.getLogger(__name__)


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
