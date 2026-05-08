"""Global Admin management endpoints (Phase 1).

Provides list / grant / revoke for the `is_global_admin` privilege.

All three endpoints require the caller to already be a global admin
(not just the internal system_user account — the system_user MAY also
manage admins, but the typical path is global-admin-to-global-admin).

Safeguards enforced here (in addition to the model column):
  * Hard cap = settings.max_global_admins (default 3).
  * Cannot self-grant or self-revoke.
  * Cannot grant or revoke against the internal system_user account.
  * Cannot revoke the last remaining global admin.
  * Every grant / revoke / failed attempt writes to audit_logs.
"""
import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.crud.audit_log import AuditLogCRUD
from app.crud.user import UserCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.models.user import User
from app.settings import settings

logger = logging.getLogger(__name__)

global_admin_router = APIRouter()

AUDIT_SOURCE = "global_admin"


class GlobalAdminUserSchema(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    is_global_admin: bool = True
    is_system_user: bool = False

    class Config:
        from_attributes = True


class GrantGlobalAdminRequest(BaseModel):
    user_id: int = Field(..., description="ID of the user to grant the global admin privilege to.")


def _record_audit(
    db_session: Session,
    actor_id: int,
    action: str,
    is_success: bool,
    details: str,
) -> None:
    """Best-effort audit log write. Never raises — audit failures must
    not block legitimate authorization work."""
    try:
        AuditLogCRUD(db_session).create_item(
            {
                "source": AUDIT_SOURCE,
                "action": action,
                "is_success": is_success,
                "details": details,
                "user_id": actor_id,
            }
        )
        db_session.commit()
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(f"Failed to write global_admin audit log: {exc}")
        db_session.rollback()


def _require_global_admin_caller(current_user: User) -> None:
    """Only existing global admins (or the internal system_user) may
    call this management API. Plain authenticated users get 403."""
    if not current_user.has_platform_bypass:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only global admins may manage global admin privileges.",
        )


def _count_global_admins(db_session: Session) -> int:
    return db_session.query(User).filter(User.is_global_admin.is_(True)).count()


@global_admin_router.get(
    "",
    response_model=List[GlobalAdminUserSchema],
    summary="List all current global admins",
)
async def list_global_admins(
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    _require_global_admin_caller(current_user)
    admins = (
        db_session.query(User)
        .filter(User.is_global_admin.is_(True))
        .order_by(User.id.asc())
        .all()
    )
    return [
        GlobalAdminUserSchema(
            id=u.id,
            email=u.email,
            first_name=u.first_name,
            last_name=u.last_name,
            is_global_admin=bool(u.is_global_admin),
            is_system_user=bool(u.is_system_user),
        )
        for u in admins
    ]


@global_admin_router.post(
    "",
    response_model=GlobalAdminUserSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Grant the global admin privilege to a user",
)
async def grant_global_admin(
    payload: GrantGlobalAdminRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    _require_global_admin_caller(current_user)

    target = UserCRUD(db_session).get_by_id(payload.user_id)
    if target is None:
        _record_audit(
            db_session, current_user.id, "grant", False,
            f"target_user_id={payload.user_id} not_found",
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target.id == current_user.id:
        _record_audit(
            db_session, current_user.id, "grant", False,
            f"target_user_id={target.id} self_grant_blocked",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot grant the global admin privilege to yourself.",
        )

    if target.is_system_user:
        _record_audit(
            db_session, current_user.id, "grant", False,
            f"target_user_id={target.id} system_user_immutable",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The internal system user cannot be modified.",
        )

    if target.is_global_admin:
        # Idempotent: already granted, return current state without
        # consuming a slot or writing a duplicate audit row.
        return GlobalAdminUserSchema(
            id=target.id,
            email=target.email,
            first_name=target.first_name,
            last_name=target.last_name,
            is_global_admin=True,
            is_system_user=bool(target.is_system_user),
        )

    if not target.is_registered or not target.hashed_password:
        _record_audit(
            db_session, current_user.id, "grant", False,
            f"target_user_id={target.id} not_registered",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target user must have completed account setup before being granted global admin.",
        )

    current_count = _count_global_admins(db_session)
    cap = settings.max_global_admins or 3
    if current_count >= cap:
        _record_audit(
            db_session, current_user.id, "grant", False,
            f"target_user_id={target.id} cap_reached current={current_count} cap={cap}",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Global admin cap reached ({current_count}/{cap}). "
                   f"Revoke an existing admin before granting another.",
        )

    target.is_global_admin = True
    db_session.flush()
    _record_audit(
        db_session, current_user.id, "grant", True,
        f"target_user_id={target.id} target_email={target.email} "
        f"new_count={current_count + 1}/{cap} ip={request.client.host if request.client else 'unknown'}",
    )
    db_session.commit()
    db_session.refresh(target)

    return GlobalAdminUserSchema(
        id=target.id,
        email=target.email,
        first_name=target.first_name,
        last_name=target.last_name,
        is_global_admin=True,
        is_system_user=bool(target.is_system_user),
    )


@global_admin_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the global admin privilege from a user",
)
async def revoke_global_admin(
    user_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    _require_global_admin_caller(current_user)

    target = UserCRUD(db_session).get_by_id(user_id)
    if target is None:
        _record_audit(
            db_session, current_user.id, "revoke", False,
            f"target_user_id={user_id} not_found",
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target.id == current_user.id:
        _record_audit(
            db_session, current_user.id, "revoke", False,
            f"target_user_id={target.id} self_revoke_blocked",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot revoke your own global admin privilege. "
                   "Ask another global admin to do it.",
        )

    if target.is_system_user:
        _record_audit(
            db_session, current_user.id, "revoke", False,
            f"target_user_id={target.id} system_user_immutable",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The internal system user cannot be modified.",
        )

    if not target.is_global_admin:
        # Idempotent revoke — already not a global admin.
        return None

    current_count = _count_global_admins(db_session)
    if current_count <= 1:
        _record_audit(
            db_session, current_user.id, "revoke", False,
            f"target_user_id={target.id} last_admin_blocked count={current_count}",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke the last remaining global admin. "
                   "Grant another admin first, or use the CLI to clear all admins.",
        )

    target.is_global_admin = False
    db_session.flush()
    _record_audit(
        db_session, current_user.id, "revoke", True,
        f"target_user_id={target.id} target_email={target.email} "
        f"remaining_count={current_count - 1} ip={request.client.host if request.client else 'unknown'}",
    )
    db_session.commit()
    return None
