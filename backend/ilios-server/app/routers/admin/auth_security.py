"""Admin endpoint to inspect recent auth security events (Phase 0B).

GET /api/admin/auth-security-events

Lists rate-limited / failed / locked logins and password-reset events.
Admin-only (uses the same has_platform_bypass gate as other admin
endpoints). No password, no token, and no raw email-of-unknown-account
is exposed — non-existent identifiers are stored only as an HMAC.
"""
import logging
from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.models.auth_security_event import AuthSecurityEvent
from app.models.user import User

logger = logging.getLogger(__name__)

auth_security_events_router = APIRouter()


class AuthSecurityEventSchema(BaseModel):
    id: int
    created_at: datetime
    event_type: str
    outcome: str
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    normalized_identifier_hash: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    reason: Optional[str] = None

    class Config:
        from_attributes = True


def _require_admin(current_user: User) -> None:
    if not getattr(current_user, "has_platform_bypass", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only global admins may view auth security events.",
        )


@auth_security_events_router.get(
    "",
    response_model=List[AuthSecurityEventSchema],
    summary="List recent auth security events.",
)
async def list_auth_security_events(
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    limit: int = Query(default=200, ge=1, le=1000),
    event_type: Optional[str] = Query(default=None),
    outcome: Optional[str] = Query(default=None),
):
    _require_admin(current_user)
    q = db_session.query(AuthSecurityEvent).outerjoin(
        User, AuthSecurityEvent.user_id == User.id
    )
    if event_type:
        q = q.filter(AuthSecurityEvent.event_type == event_type)
    if outcome:
        q = q.filter(AuthSecurityEvent.outcome == outcome)
    q = q.order_by(AuthSecurityEvent.created_at.desc()).limit(limit)
    rows = q.all()
    return [
        AuthSecurityEventSchema(
            id=row.id,
            created_at=row.created_at,
            event_type=row.event_type,
            outcome=row.outcome,
            user_id=row.user_id,
            user_email=(row.user.email if row.user else None),
            normalized_identifier_hash=row.normalized_identifier_hash,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            reason=row.reason,
        )
        for row in rows
    ]
