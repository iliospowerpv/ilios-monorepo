"""Audit Logs read API (superuser-only).

The audit trail itself is written by ``AuditingMiddleware`` (currently login /
logout events) into the ``audit_logs`` table. This router exposes a paginated,
read-only view of that table for the System Settings -> Audit Logs tab.

It is intentionally read-only: there is no create/update/delete surface here.
Access is restricted to platform-bypass users because audit details can contain
sensitive operational / account information.
"""

import logging
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud.audit_log import AuditLogCRUD
from app.db.session import get_session
from app.helpers.authorization.module_based.base import get_current_admin_user
from app.schema.user import CurrentUserSchema

audit_logs_router = APIRouter()
logger = logging.getLogger(__name__)

# Upper bound protects the DB from an unbounded scan via a hostile ``limit``.
MAX_PAGE_SIZE = 200


class AuditLogItem(BaseModel):
    id: int
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    source: Optional[str] = None
    action: Optional[str] = None
    is_success: bool
    details: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditLogsResponse(BaseModel):
    skip: int
    limit: int
    total: int
    items: List[AuditLogItem]


@audit_logs_router.get(
    "/",
    response_model=AuditLogsResponse,
    summary="List audit log entries (paginated)",
    description="Read-only, paginated audit trail. Superuser-only.",
)
async def list_audit_logs(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    skip: int = Query(0, ge=0, description="Number of rows to skip."),
    limit: int = Query(10, ge=1, le=MAX_PAGE_SIZE, description="Page size."),
    db_session: Session = Depends(get_session),
) -> AuditLogsResponse:
    """Return a page of audit log rows ordered by newest first."""
    crud = AuditLogCRUD(db_session)
    total, rows = crud.get_logs(skip=skip, limit=limit)

    items = [
        AuditLogItem(
            id=row.id,
            user_name=row.user_name,
            user_email=row.user_email,
            source=row.source,
            action=row.action,
            is_success=row.is_success,
            details=row.details,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return AuditLogsResponse(skip=skip, limit=limit, total=total, items=items)
