"""Canonical Module Permission Guards (Phase C).

This module provides FastAPI dependency functions and decorators for enforcing
module-level permissions via the Canonical Effective-Access Resolver.

NORMALIZATION RULE:
- If "edit" is present for a module, "view" is automatically included.
- This is enforced in the resolver's _normalize_permissions() function.

USAGE:
    from app.helpers.permission_guards import require_module_permission

    @router.get("/budgets")
    def get_budgets(
        company_id: int,
        current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
        db_session: Session = Depends(get_session),
    ):
        require_module_permission(
            user_id=current_user.id,
            company_id=company_id,
            db_session=db_session,
            module_key="Finance",
            action="view",
        )
        # ... endpoint logic
"""

import logging
from functools import wraps
from typing import Callable, Literal, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.access_resolver import (
    AccessDecision,
    EffectiveAccessResult,
    check_module_permission as resolver_check_module_permission,
    resolve_effective_access,
)
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsActions, PermissionsModules

logger = logging.getLogger(__name__)

ActionType = Literal["view", "edit"]


class ModulePermissionDeniedReason:
    """Reason codes for module permission denials."""
    ENTITY_ACCESS_DENIED = "entity_access_denied"
    MISSING_MODULE_PERMISSION = "missing_module_permission"


def require_module_permission(
    user_id: int,
    company_id: int,
    db_session: Session,
    module_key: str,
    action: ActionType,
    project_id: Optional[int] = None,
) -> EffectiveAccessResult:
    """Check if user has module permission and return result or raise HTTPException.
    
    This is the canonical guard for module-level permission checks.
    It uses the Canonical Effective-Access Resolver (Phase B.1) to determine access.
    
    Args:
        user_id: The user requesting access
        company_id: The company context
        db_session: Database session
        module_key: Module key (e.g., "Finance", "Asset Management")
        action: Action ("view" or "edit")
        project_id: Optional project/site ID for project-level requests
    
    Returns:
        EffectiveAccessResult if allowed
    
    Raises:
        HTTPException 403 if:
        - Entity access is denied (no applicable grants)
        - Module permission is missing (module not in effective permissions)
        - Action is not allowed (action not in module's allowed actions)
    """
    access_result = resolve_effective_access(
        user_id=user_id,
        company_id=company_id,
        db_session=db_session,
        project_id=project_id
    )
    
    if access_result.decision == AccessDecision.DENY:
        logger.warning(
            f"MODULE_PERMISSION_DENIED: user_id={user_id} module={module_key} "
            f"action={action} reason={ModulePermissionDeniedReason.ENTITY_ACCESS_DENIED} "
            f"entity_reason={access_result.reason_code} "
            f"company_id={company_id} project_id={project_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {access_result.reason_code}"
        )
    
    module_perms = access_result.effective_module_permissions.get(module_key, set())
    
    if action not in module_perms:
        reason = f"{ModulePermissionDeniedReason.MISSING_MODULE_PERMISSION}:{module_key}.{action}"
        logger.warning(
            f"MODULE_PERMISSION_DENIED: user_id={user_id} module={module_key} "
            f"action={action} reason={reason} "
            f"effective_permissions={list(module_perms)} "
            f"company_id={company_id} project_id={project_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {reason}"
        )
    
    logger.debug(
        f"MODULE_PERMISSION_GRANTED: user_id={user_id} module={module_key} "
        f"action={action} effective_role={access_result.effective_base_role} "
        f"company_id={company_id} project_id={project_id}"
    )
    
    return access_result


def create_module_permission_dependency(
    module_key: str,
    action: ActionType,
    company_id_param: str = "company_id",
    project_id_param: Optional[str] = None,
) -> Callable:
    """Create a FastAPI dependency for module permission checks.
    
    This creates a reusable dependency that can be used with Depends().
    
    Args:
        module_key: Module key (e.g., "Finance")
        action: Action ("view" or "edit")
        company_id_param: Name of the path/query parameter containing company_id
        project_id_param: Optional name of the path/query parameter containing project_id
    
    Returns:
        A dependency function that can be used with Depends()
    
    Example:
        finance_view_permission = create_module_permission_dependency(
            module_key="Finance",
            action="view",
            company_id_param="company_id"
        )
        
        @router.get("/budgets")
        def get_budgets(
            company_id: int,
            _: EffectiveAccessResult = Depends(finance_view_permission),
        ):
            ...
    """
    def dependency(
        current_user: CurrentUserSchema = Depends(get_current_user),
        db_session: Session = Depends(get_session),
        **kwargs
    ) -> EffectiveAccessResult:
        company_id = kwargs.get(company_id_param)
        project_id = kwargs.get(project_id_param) if project_id_param else None
        
        if company_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required parameter: {company_id_param}"
            )
        
        return require_module_permission(
            user_id=current_user.id,
            company_id=company_id,
            db_session=db_session,
            module_key=module_key,
            action=action,
            project_id=project_id,
        )
    
    return dependency


class ModulePermissionChecker:
    """FastAPI dependency class for module permission checks.
    
    This is a more flexible alternative to create_module_permission_dependency
    that allows dynamic company/project ID resolution.
    
    Example:
        @router.get("/companies/{company_id}/budgets")
        def get_budgets(
            company_id: int,
            current_user: CurrentUserSchema = Depends(get_current_user),
            db_session: Session = Depends(get_session),
            _permission: EffectiveAccessResult = Depends(
                ModulePermissionChecker(PermissionsModules.finance.value, "view")
            ),
        ):
            ...
    """
    
    def __init__(
        self,
        module_key: str,
        action: ActionType,
        use_site_id: bool = False,
    ):
        """Initialize the permission checker.
        
        Args:
            module_key: Module key (e.g., "Finance", "Asset Management")
            action: Action ("view" or "edit")
            use_site_id: If True, also check project-level permissions using site_id
        """
        self.module_key = module_key
        self.action = action
        self.use_site_id = use_site_id
    
    def __call__(
        self,
        company_id: Optional[int] = None,
        site_id: Optional[int] = None,
        current_user: CurrentUserSchema = Depends(get_current_user),
        db_session: Session = Depends(get_session),
    ) -> EffectiveAccessResult:
        """Check module permission and return access result."""
        if current_user.is_system_user:
            return EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="system_user",
                effective_base_role="system",
                effective_module_permissions={
                    self.module_key: {"view", "edit"}
                },
                grant_sources=[]
            )
        
        if company_id is None:
            logger.warning(
                f"MODULE_PERMISSION_DENIED: user_id={current_user.id} "
                f"module={self.module_key} action={self.action} "
                f"reason=missing_company_id"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required parameter: company_id"
            )
        
        project_id = site_id if self.use_site_id else None
        
        return require_module_permission(
            user_id=current_user.id,
            company_id=company_id,
            db_session=db_session,
            module_key=self.module_key,
            action=self.action,
            project_id=project_id,
        )


class FinanceModulePermission(ModulePermissionChecker):
    """Convenience class for Finance module permissions."""
    
    def __init__(self, action: ActionType, use_site_id: bool = False):
        super().__init__(
            module_key=PermissionsModules.finance.value,
            action=action,
            use_site_id=use_site_id,
        )


class AssetsManagementModulePermission(ModulePermissionChecker):
    """Convenience class for Asset Management module permissions."""
    
    def __init__(self, action: ActionType, use_site_id: bool = False):
        super().__init__(
            module_key=PermissionsModules.assets_management.value,
            action=action,
            use_site_id=use_site_id,
        )


class DiligenceModulePermission(ModulePermissionChecker):
    """Convenience class for Diligence module permissions."""
    
    def __init__(self, action: ActionType, use_site_id: bool = False):
        super().__init__(
            module_key=PermissionsModules.diligence.value,
            action=action,
            use_site_id=use_site_id,
        )


class OperationMaintenanceModulePermission(ModulePermissionChecker):
    """Convenience class for O&M module permissions."""
    
    def __init__(self, action: ActionType, use_site_id: bool = False):
        super().__init__(
            module_key=PermissionsModules.operation_maintenance.value,
            action=action,
            use_site_id=use_site_id,
        )


class ReportingModulePermission(ModulePermissionChecker):
    """Convenience class for Reporting module permissions."""
    
    def __init__(self, action: ActionType, use_site_id: bool = False):
        super().__init__(
            module_key=PermissionsModules.reporting.value,
            action=action,
            use_site_id=use_site_id,
        )


def get_finance_view_permission(
    company_id: int,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
) -> EffectiveAccessResult:
    """Convenience dependency for Finance:view permission."""
    if current_user.is_system_user:
        return EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="system_user",
            effective_base_role="system",
            effective_module_permissions={PermissionsModules.finance.value: {"view", "edit"}},
            grant_sources=[]
        )
    return require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="view",
    )


def get_finance_edit_permission(
    company_id: int,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
) -> EffectiveAccessResult:
    """Convenience dependency for Finance:edit permission."""
    if current_user.is_system_user:
        return EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="system_user",
            effective_base_role="system",
            effective_module_permissions={PermissionsModules.finance.value: {"view", "edit"}},
            grant_sources=[]
        )
    return require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
