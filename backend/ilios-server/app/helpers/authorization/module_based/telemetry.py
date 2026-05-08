"""Telemetry permission helpers (v2 admin scope)."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

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
