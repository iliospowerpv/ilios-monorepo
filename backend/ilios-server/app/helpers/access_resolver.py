"""Canonical Effective-Access Resolver (Restrict-Only).

This module provides a single canonical resolver used by all authorization checks.
It implements the Portfolio → Company → Project access hierarchy with restrict-only
override semantics.

Key Rules:
1. Eligibility:
   - Company-level: allowed if user has portfolio access covering company OR company access
   - Project-level: allowed if user has portfolio/company/project access

2. Restrict-Only Combination:
   - Collect all applicable grants for the target resource
   - effective_base_role = MOST RESTRICTIVE among applicable grants
     (company_admin > contributor > read_only, effective role = minimum privilege)
   - effective_module_permissions = INTERSECTION of permissions across grants

3. Intersection Semantics:
   - Permissions: {module_key: {actions: set(view/edit)}}
   - A module exists only if present in ALL applicable grants
   - Actions are intersected per module
   - edit implies view (normalized: if edit present, view is always included)

4. Explainability:
   - Returns grant_sources showing which levels contributed
   - Includes reason when denied (e.g., no_applicable_grant)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from sqlalchemy.orm import Session

from app.helpers.portfolio_hub import (
    get_portfolio_access_for_company,
    resolve_company_hub_id,
    user_has_portfolio_access_to_company,
)
from app.models.company import Company
from app.models.role_profile import RoleProfile
from app.models.site import Site
from app.models.user import (
    CompanyRole,
    MembershipStatus,
    UserCompanyAccess,
    UserPortfolioAccess,
    UserProject,
)
from app.static.permissions import PermissionsActions, PermissionsModules

logger = logging.getLogger(__name__)


class AccessDeniedReason(str, Enum):
    """Reasons why access was denied."""
    NO_APPLICABLE_GRANT = "no_applicable_grant"
    COMPANY_NOT_FOUND = "company_not_found"
    PROJECT_NOT_FOUND = "project_not_found"
    INACTIVE_MEMBERSHIP = "inactive_membership"


@dataclass
class GrantSource:
    """Source of a grant for explainability."""
    level: str  # "portfolio", "company", or "project"
    access_id: int
    role: str
    has_role_profile: bool = False
    role_profile_key: Optional[str] = None


@dataclass
class EffectiveAccessResult:
    """Result of resolve_effective_access."""
    is_allowed: bool
    effective_base_role: Optional[str] = None
    effective_module_permissions: Dict[str, Set[str]] = field(default_factory=dict)
    grant_sources: List[GrantSource] = field(default_factory=list)
    denied_reason: Optional[str] = None


# Role restrictiveness ordering (lower = more restrictive)
ROLE_RESTRICTIVENESS = {
    CompanyRole.read_only: 0,
    CompanyRole.contributor: 1,
    CompanyRole.company_admin: 2,
}


# Base role default permissions templates
# These define what permissions each base role gets when no role_profile is assigned
BASE_ROLE_DEFAULT_PERMISSIONS: Dict[CompanyRole, Dict[str, Set[str]]] = {
    CompanyRole.company_admin: {
        PermissionsModules.assets_management.value: {"view", "edit"},
        PermissionsModules.diligence.value: {"view", "edit"},
        PermissionsModules.operation_maintenance.value: {"view", "edit"},
        PermissionsModules.finance.value: {"view", "edit"},
        PermissionsModules.settings.value: {"view", "edit"},
        PermissionsModules.reporting.value: {"view", "edit"},
        PermissionsModules.investor_dashboard.value: {"view", "edit"},
        PermissionsModules.role_based_dashboard.value: {"view", "edit"},
    },
    CompanyRole.contributor: {
        PermissionsModules.assets_management.value: {"view", "edit"},
        PermissionsModules.diligence.value: {"view", "edit"},
        PermissionsModules.operation_maintenance.value: {"view", "edit"},
        PermissionsModules.finance.value: {"view"},
        PermissionsModules.reporting.value: {"view"},
    },
    CompanyRole.read_only: {
        PermissionsModules.assets_management.value: {"view"},
        PermissionsModules.diligence.value: {"view"},
        PermissionsModules.operation_maintenance.value: {"view"},
        PermissionsModules.finance.value: {"view"},
        PermissionsModules.reporting.value: {"view"},
    },
}


def _normalize_permissions(permissions: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Normalize permissions: if 'edit' is present, ensure 'view' is also present.
    
    This enforces the rule that edit implies view.
    """
    result = {}
    for module, actions in permissions.items():
        normalized_actions = set(actions)
        if "edit" in normalized_actions:
            normalized_actions.add("view")
        result[module] = normalized_actions
    return result


def _parse_module_permissions_json(
    permissions_json: Optional[Dict[str, Any]]
) -> Dict[str, Set[str]]:
    """Parse module_permissions JSON from database into normalized dict format.
    
    Input format examples:
    - {"Asset Management": {"view": true, "edit": true}}
    - {"finance": {"view": true}}
    
    Output format:
    - {"Asset Management": {"view", "edit"}}
    """
    if not permissions_json:
        return {}
    
    result = {}
    for module, actions in permissions_json.items():
        if isinstance(actions, dict):
            action_set = {k for k, v in actions.items() if v}
            if action_set:
                result[module] = action_set
    return _normalize_permissions(result)


def _get_role_profile_permissions(
    db_session: Session,
    role_profile_key: Optional[str]
) -> Optional[Dict[str, Set[str]]]:
    """Get default module permissions from a role profile."""
    if not role_profile_key:
        return None
    
    profile = db_session.query(RoleProfile).filter(
        RoleProfile.key == role_profile_key,
        RoleProfile.is_active == True
    ).first()
    
    if not profile or not profile.default_module_permissions:
        return None
    
    return _parse_module_permissions_json(profile.default_module_permissions)


def permissions_from_grant(
    grant: Union[UserPortfolioAccess, UserCompanyAccess, UserProject],
    db_session: Session
) -> Dict[str, Set[str]]:
    """Derive permissions from a grant.
    
    Priority:
    1. Start with role_profile.default_module_permissions (if role_profile_key set)
       Otherwise use base-role default permissions template
    2. Apply module_permissions override JSON (if present) at grant level
       - Override replaces the module entry, not merges
    
    Returns normalized permissions dict.
    """
    # Get base permissions from role profile or base role defaults
    role_profile_key: Optional[str] = getattr(grant, 'role_profile_key', None)
    grant_role: CompanyRole = grant.role  # type: ignore[assignment]
    
    if role_profile_key:
        base_permissions = _get_role_profile_permissions(db_session, role_profile_key)
        if base_permissions is None:
            # Fallback to base role if profile not found/inactive
            base_permissions = {
                k: set(v) for k, v in 
                BASE_ROLE_DEFAULT_PERMISSIONS.get(grant_role, {}).items()
            }
    else:
        base_permissions = {
            k: set(v) for k, v in 
            BASE_ROLE_DEFAULT_PERMISSIONS.get(grant_role, {}).items()
        }
    
    # Apply module_permissions override if present
    module_overrides: Optional[Dict[str, Any]] = getattr(grant, 'module_permissions', None)
    if module_overrides:
        parsed_overrides = _parse_module_permissions_json(module_overrides)
        # Overrides replace modules (restrict-only: can only narrow, not expand)
        for module, actions in parsed_overrides.items():
            if module in base_permissions:
                # Intersection: can only restrict, not expand
                base_permissions[module] = base_permissions[module] & actions
            # Don't add new modules via override (restrict-only)
    
    return _normalize_permissions(base_permissions)


def intersect_permissions(
    permissions_list: List[Dict[str, Set[str]]]
) -> Dict[str, Set[str]]:
    """Compute intersection of multiple permission sets.
    
    A module exists in result only if present in ALL permission sets.
    Actions per module are intersected.
    
    Returns empty dict if any permission set is empty or list is empty.
    """
    if not permissions_list:
        return {}
    
    if len(permissions_list) == 1:
        return _normalize_permissions(permissions_list[0])
    
    # Start with first set
    result = {k: set(v) for k, v in permissions_list[0].items()}
    
    # Intersect with remaining sets
    for perm_set in permissions_list[1:]:
        # Only keep modules present in both
        common_modules = set(result.keys()) & set(perm_set.keys())
        new_result = {}
        for module in common_modules:
            # Intersect actions
            intersected_actions = result[module] & perm_set.get(module, set())
            if intersected_actions:
                new_result[module] = intersected_actions
        result = new_result
    
    return _normalize_permissions(result)


def effective_base_role_from_grants(
    grants: List[Union[UserPortfolioAccess, UserCompanyAccess, UserProject]]
) -> Optional[CompanyRole]:
    """Get the most restrictive base role from a list of grants.
    
    Most restrictive wins: read_only < contributor < company_admin
    """
    if not grants:
        return None
    
    # Get the minimum (most restrictive) role
    roles: List[CompanyRole] = []
    for g in grants:
        role: CompanyRole = g.role  # type: ignore[assignment]
        if role:
            roles.append(role)
    
    if not roles:
        return None
    
    return min(roles, key=lambda r: ROLE_RESTRICTIVENESS.get(r, 0))


def get_applicable_grants(
    user_id: int,
    company_id: int,
    db_session: Session,
    project_id: Optional[int] = None
) -> Tuple[
    Optional[UserPortfolioAccess],
    Optional[UserCompanyAccess],
    Optional[UserProject]
]:
    """Get all applicable grants for the target resource.
    
    Returns tuple of (portfolio_grant, company_grant, project_grant).
    Each may be None if not applicable.
    """
    portfolio_grant = None
    company_grant = None
    project_grant = None
    
    # Get portfolio grant that covers this company
    portfolio_grant = get_portfolio_access_for_company(user_id, company_id, db_session)
    
    # Get direct company access
    company_grant = db_session.query(UserCompanyAccess).filter(
        UserCompanyAccess.user_id == user_id,
        UserCompanyAccess.company_id == company_id,
        UserCompanyAccess.status == MembershipStatus.active
    ).first()
    
    # Get project access if project_id provided
    if project_id:
        project_grant = db_session.query(UserProject).filter(
            UserProject.user_id == user_id,
            UserProject.site_id == project_id,
            UserProject.status == MembershipStatus.active
        ).first()
    
    return portfolio_grant, company_grant, project_grant


def resolve_effective_access(
    user_id: int,
    company_id: int,
    db_session: Session,
    project_id: Optional[int] = None
) -> EffectiveAccessResult:
    """Resolve effective access for a user to a company or project.
    
    This is the canonical resolver used by all authorization checks.
    
    Args:
        user_id: The user requesting access
        company_id: The company context
        db_session: Database session
        project_id: Optional project/site ID for project-level requests
    
    Returns:
        EffectiveAccessResult with:
        - is_allowed: Whether access is granted
        - effective_base_role: Most restrictive role from applicable grants
        - effective_module_permissions: Intersection of permissions
        - grant_sources: List of grants that contributed
        - denied_reason: Reason if denied
    """
    # Verify company exists
    company = db_session.query(Company).get(company_id)
    if not company:
        return EffectiveAccessResult(
            is_allowed=False,
            denied_reason=AccessDeniedReason.COMPANY_NOT_FOUND.value
        )
    
    # Verify project exists if specified
    if project_id:
        project = db_session.query(Site).get(project_id)
        if not project:
            return EffectiveAccessResult(
                is_allowed=False,
                denied_reason=AccessDeniedReason.PROJECT_NOT_FOUND.value
            )
    
    # Get all applicable grants
    portfolio_grant, company_grant, project_grant = get_applicable_grants(
        user_id, company_id, db_session, project_id
    )
    
    # Build list of applicable grants for this request
    applicable_grants = []
    grant_sources = []
    
    # Portfolio grant (if it covers this company)
    if portfolio_grant:
        applicable_grants.append(portfolio_grant)
        portfolio_role: CompanyRole = portfolio_grant.role  # type: ignore[assignment]
        grant_sources.append(GrantSource(
            level="portfolio",
            access_id=int(portfolio_grant.id),  # type: ignore[arg-type]
            role=portfolio_role.value,
            has_role_profile=False,  # Portfolio access doesn't have role_profile
            role_profile_key=None
        ))
    
    # Company grant
    if company_grant:
        applicable_grants.append(company_grant)
        company_role: CompanyRole = company_grant.role  # type: ignore[assignment]
        company_profile_key: Optional[str] = company_grant.role_profile_key  # type: ignore[assignment]
        grant_sources.append(GrantSource(
            level="company",
            access_id=int(company_grant.id),  # type: ignore[arg-type]
            role=company_role.value,
            has_role_profile=bool(company_profile_key),
            role_profile_key=company_profile_key
        ))
    
    # Project grant (only for project-level requests)
    if project_id and project_grant:
        applicable_grants.append(project_grant)
        project_role: CompanyRole = project_grant.role  # type: ignore[assignment]
        grant_sources.append(GrantSource(
            level="project",
            access_id=int(project_grant.id),  # type: ignore[arg-type]
            role=project_role.value,
            has_role_profile=False,  # UserProject doesn't have role_profile
            role_profile_key=None
        ))
    
    # Check eligibility
    if project_id:
        # Project-level: need at least one of portfolio/company/project access
        if not applicable_grants:
            return EffectiveAccessResult(
                is_allowed=False,
                denied_reason=AccessDeniedReason.NO_APPLICABLE_GRANT.value
            )
    else:
        # Company-level: need portfolio or company access
        if not portfolio_grant and not company_grant:
            return EffectiveAccessResult(
                is_allowed=False,
                denied_reason=AccessDeniedReason.NO_APPLICABLE_GRANT.value
            )
    
    # Compute effective base role (most restrictive)
    effective_role = effective_base_role_from_grants(applicable_grants)
    
    # Compute effective module permissions (intersection)
    permissions_list = [
        permissions_from_grant(grant, db_session)
        for grant in applicable_grants
    ]
    effective_permissions = intersect_permissions(permissions_list)
    
    return EffectiveAccessResult(
        is_allowed=True,
        effective_base_role=effective_role.value if effective_role else None,
        effective_module_permissions=effective_permissions,
        grant_sources=grant_sources
    )


def check_module_permission(
    access_result: EffectiveAccessResult,
    module: str,
    action: str
) -> Tuple[bool, Optional[str]]:
    """Check if a specific module permission is granted.
    
    Args:
        access_result: Result from resolve_effective_access
        module: Module key (e.g., "Asset Management")
        action: Action (e.g., "view", "edit")
    
    Returns:
        Tuple of (is_allowed, denied_reason)
    """
    if not access_result.is_allowed:
        return False, access_result.denied_reason
    
    module_perms = access_result.effective_module_permissions.get(module, set())
    if action not in module_perms:
        return False, f"missing_permission_{module}.{action}"
    
    return True, None


def require_effective_permission(
    user_id: int,
    company_id: int,
    db_session: Session,
    module: str,
    action: str,
    project_id: Optional[int] = None
) -> EffectiveAccessResult:
    """Check if user has permission and return result or raise HTTPException.
    
    This is a convenience wrapper for route handlers to use the resolver.
    
    Args:
        user_id: The user requesting access
        company_id: The company context
        db_session: Database session
        module: Module key (e.g., "Asset Management")
        action: Action (e.g., "view", "edit")
        project_id: Optional project/site ID for project-level requests
    
    Returns:
        EffectiveAccessResult if allowed
    
    Raises:
        HTTPException with 403 if denied
    
    Example usage in a route handler:
        @router.get("/sites/{site_id}")
        def get_site(
            site_id: int,
            current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
            db: Session = Depends(get_db)
        ):
            site = db.query(Site).get(site_id)
            access = require_effective_permission(
                user_id=current_user.id,
                company_id=site.company_id,
                db_session=db,
                module="Asset Management",
                action="view",
                project_id=site_id
            )
            # access.effective_base_role, access.grant_sources available for auditing
            return site
    """
    from fastapi import HTTPException, status
    
    access_result = resolve_effective_access(
        user_id=user_id,
        company_id=company_id,
        db_session=db_session,
        project_id=project_id
    )
    
    allowed, reason = check_module_permission(access_result, module, action)
    
    if not allowed:
        logger.warning(
            f"User {user_id} denied access to {module}.{action} "
            f"(company={company_id}, project={project_id}): {reason}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {reason}"
        )
    
    return access_result
