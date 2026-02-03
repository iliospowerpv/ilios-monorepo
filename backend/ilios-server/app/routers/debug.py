"""Debug Endpoints for Authorization Triage (Phase C.1.2).

This module provides admin-only debug endpoints to inspect effective access
and module permissions for troubleshooting 403 errors.

SECURITY:
- All endpoints require company_admin or higher role
- Exposes grant details (including IDs) - admin-only visibility

USAGE:
    GET /api/debug/effective-access?user_id=123&company_id=456&project_id=789
"""

import logging
from typing import Annotated, Any, Dict, List, Optional, Set

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud.user import UserCRUD
from app.db.session import get_session
from app.helpers.access_resolver import (
    AccessDecision,
    EffectiveAccessResult,
    GrantSource,
    resolve_effective_access,
)
from app.helpers.authentication import get_current_user
from app.models.user import CompanyRole, UserCompanyAccess, MembershipStatus
from app.schema.user import CurrentUserSchema

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["Debug"])


class GrantSourceResponse(BaseModel):
    """Response model for a grant source."""
    level: str
    access_id: int
    role: str
    has_role_profile: bool
    role_profile_key: Optional[str] = None


class EffectiveAccessResponse(BaseModel):
    """Response model for effective access debug endpoint."""
    decision: str
    reason_code: str
    effective_base_role: Optional[str] = None
    effective_module_permissions: Dict[str, List[str]] = {}
    grant_sources: List[GrantSourceResponse] = []
    context: Dict[str, Any] = {}

    class Config:
        json_schema_extra = {
            "example": {
                "decision": "allow",
                "reason_code": "access_granted",
                "effective_base_role": "contributor",
                "effective_module_permissions": {
                    "Finance": ["view"],
                    "Asset Management": ["view", "edit"]
                },
                "grant_sources": [
                    {
                        "level": "company",
                        "access_id": 123,
                        "role": "contributor",
                        "has_role_profile": True,
                        "role_profile_key": "asset_manager"
                    }
                ],
                "context": {
                    "user_id": 456,
                    "company_id": 789,
                    "project_id": None
                }
            }
        }


def _require_admin_access(
    current_user: CurrentUserSchema,
    db_session: Session,
    target_company_id: int,
) -> None:
    """Verify the requesting user has admin access to view debug info for the target company.
    
    Requirements (strict - no cross-company visibility):
    - User must be system user OR
    - User must have company_admin role on the TARGET company
    
    This prevents cross-company data leakage via debug endpoints.
    """
    if current_user.is_system_user:
        return
    
    access = db_session.query(UserCompanyAccess).filter(
        UserCompanyAccess.user_id == current_user.id,
        UserCompanyAccess.company_id == target_company_id,
        UserCompanyAccess.role == CompanyRole.company_admin,
        UserCompanyAccess.status == MembershipStatus.active,
    ).first()
    
    if access:
        return
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "access_denied",
            "reason_code": "admin_required_for_target_company",
            "message": f"Debug endpoints require company_admin role on company {target_company_id}"
        }
    )


@router.get("/effective-access", response_model=EffectiveAccessResponse)
def get_effective_access(
    user_id: int = Query(..., description="User ID to check access for"),
    company_id: int = Query(..., description="Company context"),
    project_id: Optional[int] = Query(None, description="Project/site context (optional)"),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)] = None,
    db_session: Session = Depends(get_session),
) -> EffectiveAccessResponse:
    """Get effective access details for a user in a given context.
    
    This is an admin-only debug endpoint for troubleshooting 403 errors.
    It returns the full effective access result including:
    - decision (allow/deny)
    - reason_code
    - effective_base_role
    - effective_module_permissions (normalized)
    - grant_sources (which grants contributed)
    
    Security:
    - Requires company_admin role on the target company or any company
    """
    _require_admin_access(current_user, db_session, company_id)
    
    user_crud = UserCRUD(db_session)
    target_user = user_crud.get_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"User {user_id} not found"}
        )
    
    access_result = resolve_effective_access(
        user_id=user_id,
        company_id=company_id,
        db_session=db_session,
        project_id=project_id,
    )
    
    logger.info(
        f"DEBUG_EFFECTIVE_ACCESS: admin_user={current_user.id} "
        f"target_user={user_id} company={company_id} project={project_id} "
        f"decision={access_result.decision.value}"
    )
    
    permissions_response = {
        module: list(actions)
        for module, actions in access_result.effective_module_permissions.items()
    }
    
    grant_sources_response = [
        GrantSourceResponse(
            level=gs.level,
            access_id=gs.access_id,
            role=gs.role,
            has_role_profile=gs.has_role_profile,
            role_profile_key=gs.role_profile_key,
        )
        for gs in access_result.grant_sources
    ]
    
    return EffectiveAccessResponse(
        decision=access_result.decision.value,
        reason_code=access_result.reason_code,
        effective_base_role=access_result.effective_base_role,
        effective_module_permissions=permissions_response,
        grant_sources=grant_sources_response,
        context={
            "user_id": user_id,
            "company_id": company_id,
            "project_id": project_id,
        }
    )


@router.get("/module-permission-check")
def check_module_permission_debug(
    user_id: int = Query(..., description="User ID to check"),
    company_id: int = Query(..., description="Company context"),
    module_key: str = Query(..., description="Module to check (e.g., 'Finance')"),
    action: str = Query("view", description="Action to check ('view' or 'edit')"),
    project_id: Optional[int] = Query(None, description="Project/site context (optional)"),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)] = None,
    db_session: Session = Depends(get_session),
) -> Dict[str, Any]:
    """Check if a user has a specific module permission in a given context.
    
    Returns detailed information about why the permission was granted or denied,
    useful for debugging 403 errors.
    """
    _require_admin_access(current_user, db_session, company_id)
    
    user_crud = UserCRUD(db_session)
    target_user = user_crud.get_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"User {user_id} not found"}
        )
    
    access_result = resolve_effective_access(
        user_id=user_id,
        company_id=company_id,
        db_session=db_session,
        project_id=project_id,
    )
    
    if access_result.decision == AccessDecision.DENY:
        return {
            "permission_granted": False,
            "reason": "entity_access_denied",
            "entity_reason_code": access_result.reason_code,
            "module_key": module_key,
            "action": action,
            "effective_module_permissions": {},
            "triage_hint": f"Check {access_result.reason_code} in triage checklist",
        }
    
    module_perms = access_result.effective_module_permissions.get(module_key, set())
    has_permission = action in module_perms
    
    permissions_response = {
        module: list(actions)
        for module, actions in access_result.effective_module_permissions.items()
    }
    
    if has_permission:
        triage_hint = None
    else:
        if module_key not in access_result.effective_module_permissions:
            triage_hint = f"Module '{module_key}' not in effective permissions. Check role_profile defaults or grant overrides."
        else:
            triage_hint = f"Action '{action}' not in module permissions {list(module_perms)}. Check role_profile or grant overrides."
    
    return {
        "permission_granted": has_permission,
        "reason": "allowed" if has_permission else "missing_module_permission",
        "module_key": module_key,
        "action": action,
        "module_permissions_for_key": list(module_perms),
        "all_effective_permissions": permissions_response,
        "effective_base_role": access_result.effective_base_role,
        "grant_sources": [
            {
                "level": gs.level,
                "access_id": gs.access_id,
                "role": gs.role,
                "role_profile_key": gs.role_profile_key,
            }
            for gs in access_result.grant_sources
        ],
        "triage_hint": triage_hint,
    }
