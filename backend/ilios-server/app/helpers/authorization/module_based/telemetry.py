"""Telemetry permission helpers (v2 admin scope)."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.crud.user_company_access import UserCompanyAccessCRUD
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema

logger = logging.getLogger(__name__)

TELEMETRY_PERMISSION_MODULE = "Telemetry"
TELEMETRY_ADMIN_ACTION = "admin"


class TelemetryPermissions:
    """FastAPI dependency for ``telemetry:admin``.

    System users bypass the check. Otherwise the active role must hold
    ``Telemetry.admin`` (or be a company admin via the legacy
    ``Settings Page.edit`` permission, which is auto-granted on seed).
    """

    def __init__(self, action: str = TELEMETRY_ADMIN_ACTION) -> None:
        self.action = action

    def __call__(
        self,
        current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
        request: Request,
    ) -> CurrentUserSchema:
        if getattr(current_user, "has_platform_bypass", False):
            return current_user

        role = getattr(current_user, "role", None)
        permissions = getattr(role, "permissions", None) or {}
        telemetry_perms = permissions.get(TELEMETRY_PERMISSION_MODULE) or {}

        if telemetry_perms.get(self.action):
            return current_user

        # Legacy fallback: settings:edit grants telemetry:admin until the
        # frontend wires a dedicated UI for managing the new permission.
        settings_perms = permissions.get("Settings Page") or {}
        if settings_perms.get("edit"):
            return current_user

        logger.info(
            "Telemetry permission denied user_id=%s action=%s",
            getattr(current_user, "id", None),
            self.action,
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Telemetry admin permission required")


telemetry_admin_required = TelemetryPermissions(TELEMETRY_ADMIN_ACTION)


def user_has_telemetry_admin(current_user: CurrentUserSchema) -> bool:
    """Non-throwing variant of :class:`TelemetryPermissions` for read paths.

    Use this when an endpoint is open to any company-visible user but
    needs to gate sensitive metadata (e.g. credential fingerprints) to
    telemetry administrators only.
    """
    if getattr(current_user, "has_platform_bypass", False):
        return True
    role = getattr(current_user, "role", None)
    permissions = getattr(role, "permissions", None) or {}
    telemetry_perms = permissions.get(TELEMETRY_PERMISSION_MODULE) or {}
    if telemetry_perms.get(TELEMETRY_ADMIN_ACTION):
        return True
    settings_perms = permissions.get("Settings Page") or {}
    return bool(settings_perms.get("edit"))


# ---------------------------------------------------------------------------
# Baseline lifecycle authority (Phase 0 hardening)
#
# Lifecycle mutations (approve / activate) require BOTH telemetry-admin AND
# company-admin for the baseline's owning company (or platform bypass). This is
# the backend source of truth; the frontend mirrors it via server-computed
# capability flags (it never re-derives company-admin locally). Draft-authoring
# and read-only review stay at telemetry-admin + site access (unchanged).
# ---------------------------------------------------------------------------

_LIFECYCLE_REQUIRED_ROLES = ["telemetry_admin", "company_admin"]

_LIFECYCLE_REASON_MESSAGES = {
    "telemetry_admin_required": (
        "This action requires Telemetry admin permission."
    ),
    "company_admin_required": (
        "This action requires Company admin for this baseline's company in "
        "addition to Telemetry admin."
    ),
}


class BaselineLifecycleForbiddenError(Exception):
    """Raised when a user lacks authority for a baseline lifecycle mutation.

    Rendered as a structured 403 by :func:`baseline_lifecycle_forbidden_handler`
    (registered in ``app.main``) so the action and reason are machine-readable
    rather than flattened to a string by the generic HTTP handler.
    """

    def __init__(
        self,
        *,
        action_code: str,
        reason_code: str,
        company_id: int,
    ) -> None:
        self.action_code = action_code
        self.reason_code = reason_code
        self.company_id = company_id
        self.message = _LIFECYCLE_REASON_MESSAGES.get(
            reason_code, "Not authorized for this baseline action."
        )
        super().__init__(self.message)


def user_is_company_admin(
    db: Session, current_user: CurrentUserSchema, company_id: int
) -> bool:
    """True when the user is a platform-bypass user or an active company admin.

    Company-admin is the backend truth (active ``user_company_access`` membership
    with ``role == company_admin`` for ``company_id``) — never a global role
    permission. Non-throwing; used both for enforcement and capability flags.
    """
    if getattr(current_user, "has_platform_bypass", False):
        return True
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        return False
    return UserCompanyAccessCRUD(db).is_company_admin(user_id, company_id)


def can_author_draft(current_user: CurrentUserSchema) -> bool:
    """Draft-authoring capability = telemetry-admin (site access enforced by route)."""
    return user_has_telemetry_admin(current_user)


def can_manage_baseline_lifecycle(
    db: Session, current_user: CurrentUserSchema, company_id: int
) -> bool:
    """Lifecycle capability = telemetry-admin AND company-admin (or bypass)."""
    return user_has_telemetry_admin(current_user) and user_is_company_admin(
        db, current_user, company_id
    )


def enforce_baseline_lifecycle_authority(
    db: Session,
    current_user: CurrentUserSchema,
    *,
    company_id: int,
    action_code: str,
) -> None:
    """Fail-closed gate for baseline lifecycle mutations (approve/activate).

    Site visibility is enforced separately by the route (resolver). This adds the
    governance requirement: telemetry-admin AND company-admin for ``company_id``.
    Raises :class:`BaselineLifecycleForbiddenError` (structured 403) otherwise.
    Performs no writes, so callers can run it before any mutation.
    """
    if getattr(current_user, "has_platform_bypass", False):
        return
    if not user_has_telemetry_admin(current_user):
        raise BaselineLifecycleForbiddenError(
            action_code=action_code,
            reason_code="telemetry_admin_required",
            company_id=company_id,
        )
    if not user_is_company_admin(db, current_user, company_id):
        logger.info(
            "Baseline lifecycle denied user_id=%s company_id=%s action=%s "
            "reason=company_admin_required",
            getattr(current_user, "id", None),
            company_id,
            action_code,
        )
        raise BaselineLifecycleForbiddenError(
            action_code=action_code,
            reason_code="company_admin_required",
            company_id=company_id,
        )


async def baseline_lifecycle_forbidden_handler(
    request: Request, exception: BaselineLifecycleForbiddenError  # noqa: U100
):
    """Render :class:`BaselineLifecycleForbiddenError` as a structured 403 body."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": f"baseline_{exception.action_code}_forbidden",
            "action": exception.action_code,
            "reason": exception.reason_code,
            "message": exception.message,
            "required_roles": list(_LIFECYCLE_REQUIRED_ROLES),
        },
    )
