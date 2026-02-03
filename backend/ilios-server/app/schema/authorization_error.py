"""Standardized 403 Authorization Error Schema (Phase C.1.2).

This module provides a standardized schema for 403 Access Denied responses
to make them actionable for debugging and triage.

Error Response Format:
{
    "error": "access_denied",
    "reason_code": "missing_module_permission",
    "module_key": "Finance",           # Only when reason_code = missing_module_permission
    "action": "edit",                  # Only when reason_code = missing_module_permission
    "grant_sources_summary": {         # Safe summary (no sensitive IDs)
        "levels_checked": ["company", "project"],
        "grants_found": 1
    }
}
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class GrantSourcesSummary(BaseModel):
    """Safe summary of grant sources (no sensitive IDs exposed)."""
    levels_checked: List[str] = []
    grants_found: int = 0


class AuthorizationErrorDetail(BaseModel):
    """Standardized 403 error response detail.
    
    This schema is used for all 403 Access Denied responses to provide
    actionable debugging information.
    
    Fields:
        error: Always "access_denied"
        reason_code: One of the AccessDeniedReason values or module permission reason
        module_key: Module that was checked (only for missing_module_permission)
        action: Action that was attempted (only for missing_module_permission)
        grant_sources_summary: Safe summary of grants checked (no sensitive IDs)
        context: Additional context (company_id, project_id - only for admin visibility)
    """
    error: str = "access_denied"
    reason_code: str
    module_key: Optional[str] = None
    action: Optional[str] = None
    grant_sources_summary: Optional[GrantSourcesSummary] = None
    context: Optional[Dict[str, Any]] = None  # Only included for admin users
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "access_denied",
                "reason_code": "missing_module_permission",
                "module_key": "Finance",
                "action": "edit",
                "grant_sources_summary": {
                    "levels_checked": ["company"],
                    "grants_found": 1
                }
            }
        }


def create_authorization_error(
    reason_code: str,
    module_key: Optional[str] = None,
    action: Optional[str] = None,
    grant_sources: Optional[List[Any]] = None,
    company_id: Optional[int] = None,
    project_id: Optional[int] = None,
    include_context: bool = False,
) -> Dict[str, Any]:
    """Create a standardized authorization error response.
    
    Args:
        reason_code: The reason for denial (e.g., "no_applicable_grant", "missing_module_permission")
        module_key: Module that was checked (for missing_module_permission)
        action: Action that was attempted (for missing_module_permission)
        grant_sources: List of GrantSource objects from resolver
        company_id: Company context (only included if include_context=True)
        project_id: Project context (only included if include_context=True)
        include_context: Whether to include company/project IDs (admin-only)
    
    Returns:
        Dict suitable for HTTPException detail
    """
    error = {
        "error": "access_denied",
        "reason_code": reason_code,
    }
    
    if module_key:
        error["module_key"] = module_key
    if action:
        error["action"] = action
    
    if grant_sources is not None:
        levels_checked = list(set(gs.level for gs in grant_sources)) if grant_sources else []
        error["grant_sources_summary"] = {
            "levels_checked": levels_checked,
            "grants_found": len(grant_sources) if grant_sources else 0
        }
    
    if include_context:
        context = {}
        if company_id is not None:
            context["company_id"] = company_id
        if project_id is not None:
            context["project_id"] = project_id
        if context:
            error["context"] = context
    
    return error


class AuthorizationErrorReasonCodes:
    """Standardized reason codes for authorization errors.
    
    Use these for triage and debugging.
    """
    # Entity-level denials (from access_resolver)
    NO_APPLICABLE_GRANT = "no_applicable_grant"
    COMPANY_NOT_FOUND = "company_not_found"
    PROJECT_NOT_FOUND = "project_not_found"
    INACTIVE_MEMBERSHIP = "inactive_membership"
    UNDETERMINED_CONTEXT = "undetermined_context"
    PROJECT_COMPANY_MISMATCH = "project_company_mismatch"
    SYSTEM_ERROR = "system_error"
    
    # Module-level denials (from permission_guards)
    MISSING_MODULE_PERMISSION = "missing_module_permission"
    ENTITY_ACCESS_DENIED = "entity_access_denied"
    NO_ACCESSIBLE_CONTEXT = "no_accessible_context"
