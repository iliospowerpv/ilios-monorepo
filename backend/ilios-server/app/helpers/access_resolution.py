"""Centralized access resolution for computed/inherited access model.

This module provides consistent access resolution across all endpoints,
implementing the precedence and status blocking rules defined in
docs/access_model_audit.md.

Precedence Rules:
- Direct beats inherited (most specific wins)
- Project > Company > Portfolio
- Disabled at any level blocks inherited access

Status Blocking:
- If a source is disabled, inherited access through that source is blocked
- Direct grants are always shown (even if disabled) but don't grant access

Access Source Priority:
1. direct_project (most specific)
2. direct_company
3. inherited_company (project inherits from company)
4. inherited_portfolio (company/project inherits from portfolio)
5. project_only (user sees company via project)
6. project_context (company visible for project context)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any

from app.schema.user_company_access import CompanyRoleEnum, MembershipStatusEnum


class ResolvedAccessSource(str, Enum):
    """Resolved source after precedence is applied."""
    direct_company = "direct_company"
    direct_project = "direct_project"
    inherited_portfolio = "inherited_portfolio"
    inherited_company = "inherited_company"
    project_only = "project_only"
    project_context = "project_context"


@dataclass
class AccessGrant:
    """Represents an access grant from a single source."""
    source: ResolvedAccessSource
    role: Optional[CompanyRoleEnum]
    status: MembershipStatusEnum
    membership_id: Optional[int] = None


@dataclass
class ResolvedAccess:
    """Result of access resolution across all sources."""
    has_access: bool
    access_source: ResolvedAccessSource
    resolved_role: CompanyRoleEnum
    resolved_status: MembershipStatusEnum
    membership_id: Optional[int]
    direct_role: Optional[CompanyRoleEnum] = None
    inherited_role: Optional[CompanyRoleEnum] = None
    all_sources: Optional[List[ResolvedAccessSource]] = None


SOURCE_PRIORITY = [
    ResolvedAccessSource.direct_project,
    ResolvedAccessSource.direct_company,
    ResolvedAccessSource.inherited_company,
    ResolvedAccessSource.inherited_portfolio,
    ResolvedAccessSource.project_only,
    ResolvedAccessSource.project_context,
]


def resolve_company_access(
    direct_grant: Optional[AccessGrant],
    portfolio_grant: Optional[AccessGrant],
    project_only_grant: Optional[AccessGrant],
) -> ResolvedAccess:
    """Resolve access to a company from multiple sources.
    
    Precedence: direct_company > inherited_portfolio > project_only
    
    Status Blocking Rules:
    - Direct grant always wins (even if disabled - shown but no access)
    - Disabled portfolio BLOCKS ALL inherited access including project_only
    - Project_only is only considered if no portfolio grant exists
    
    Args:
        direct_grant: Direct UserCompanyAccess grant if exists
        portfolio_grant: UserPortfolioAccess grant if exists  
        project_only_grant: UserProject grant (project context) if exists
    
    Returns:
        ResolvedAccess with winning source and resolved role/status
    """
    grants = []
    if direct_grant:
        grants.append(direct_grant)
    if portfolio_grant:
        grants.append(portfolio_grant)
    if project_only_grant:
        grants.append(project_only_grant)
    
    if not grants:
        return ResolvedAccess(
            has_access=False,
            access_source=ResolvedAccessSource.direct_company,
            resolved_role=CompanyRoleEnum.contributor,
            resolved_status=MembershipStatusEnum.disabled,
            membership_id=None,
        )
    
    all_sources = [g.source for g in grants]
    
    direct_role = direct_grant.role if direct_grant else None
    inherited_role = portfolio_grant.role if portfolio_grant else (
        project_only_grant.role if project_only_grant else None
    )
    
    if direct_grant:
        return ResolvedAccess(
            has_access=direct_grant.status == MembershipStatusEnum.active,
            access_source=ResolvedAccessSource.direct_company,
            resolved_role=direct_grant.role or CompanyRoleEnum.contributor,
            resolved_status=direct_grant.status,
            membership_id=direct_grant.membership_id,
            direct_role=direct_role,
            inherited_role=inherited_role,
            all_sources=all_sources,
        )
    
    if portfolio_grant:
        if portfolio_grant.status == MembershipStatusEnum.disabled:
            return ResolvedAccess(
                has_access=False,
                access_source=ResolvedAccessSource.inherited_portfolio,
                resolved_role=portfolio_grant.role or CompanyRoleEnum.contributor,
                resolved_status=MembershipStatusEnum.disabled,
                membership_id=None,
                direct_role=None,
                inherited_role=portfolio_grant.role,
                all_sources=all_sources,
            )
        return ResolvedAccess(
            has_access=portfolio_grant.status == MembershipStatusEnum.active,
            access_source=ResolvedAccessSource.inherited_portfolio,
            resolved_role=portfolio_grant.role or CompanyRoleEnum.contributor,
            resolved_status=portfolio_grant.status,
            membership_id=None,
            direct_role=None,
            inherited_role=portfolio_grant.role,
            all_sources=all_sources,
        )
    
    if project_only_grant:
        return ResolvedAccess(
            has_access=project_only_grant.status == MembershipStatusEnum.active,
            access_source=ResolvedAccessSource.project_only,
            resolved_role=project_only_grant.role or CompanyRoleEnum.contributor,
            resolved_status=project_only_grant.status,
            membership_id=None,
            direct_role=None,
            inherited_role=project_only_grant.role,
            all_sources=all_sources,
        )
    
    return ResolvedAccess(
        has_access=False,
        access_source=ResolvedAccessSource.direct_company,
        resolved_role=CompanyRoleEnum.contributor,
        resolved_status=MembershipStatusEnum.disabled,
        membership_id=None,
    )


def resolve_project_access(
    direct_grant: Optional[AccessGrant],
    company_grant: Optional[AccessGrant],
    portfolio_grant: Optional[AccessGrant],
) -> ResolvedAccess:
    """Resolve access to a project from multiple sources.
    
    Precedence: direct_project > inherited_company > inherited_portfolio
    
    Status Blocking Rules:
    - Direct project grant always wins (even if disabled - shown but no access)
    - Disabled company blocks inherited company access to projects
    - Disabled portfolio blocks inherited portfolio access to projects
    - Disabled at higher level blocks lower level inherited access
    
    Args:
        direct_grant: Direct UserProject grant if exists
        company_grant: UserCompanyAccess grant (inherited) if exists
        portfolio_grant: UserPortfolioAccess grant (inherited) if exists
    
    Returns:
        ResolvedAccess with winning source and resolved role/status
    """
    grants = []
    if direct_grant:
        grants.append(direct_grant)
    if company_grant:
        grants.append(company_grant)
    if portfolio_grant:
        grants.append(portfolio_grant)
    
    if not grants:
        return ResolvedAccess(
            has_access=False,
            access_source=ResolvedAccessSource.direct_project,
            resolved_role=CompanyRoleEnum.contributor,
            resolved_status=MembershipStatusEnum.disabled,
            membership_id=None,
        )
    
    all_sources = [g.source for g in grants]
    
    if direct_grant:
        return ResolvedAccess(
            has_access=direct_grant.status == MembershipStatusEnum.active,
            access_source=ResolvedAccessSource.direct_project,
            resolved_role=direct_grant.role or CompanyRoleEnum.contributor,
            resolved_status=direct_grant.status,
            membership_id=direct_grant.membership_id,
            all_sources=all_sources,
        )
    
    if company_grant:
        if company_grant.status == MembershipStatusEnum.disabled:
            return ResolvedAccess(
                has_access=False,
                access_source=ResolvedAccessSource.inherited_company,
                resolved_role=company_grant.role or CompanyRoleEnum.contributor,
                resolved_status=MembershipStatusEnum.disabled,
                membership_id=None,
                all_sources=all_sources,
            )
        return ResolvedAccess(
            has_access=True,
            access_source=ResolvedAccessSource.inherited_company,
            resolved_role=company_grant.role or CompanyRoleEnum.contributor,
            resolved_status=company_grant.status,
            membership_id=None,
            all_sources=all_sources,
        )
    
    if portfolio_grant:
        if portfolio_grant.status == MembershipStatusEnum.disabled:
            return ResolvedAccess(
                has_access=False,
                access_source=ResolvedAccessSource.inherited_portfolio,
                resolved_role=portfolio_grant.role or CompanyRoleEnum.contributor,
                resolved_status=MembershipStatusEnum.disabled,
                membership_id=None,
                all_sources=all_sources,
            )
        return ResolvedAccess(
            has_access=True,
            access_source=ResolvedAccessSource.inherited_portfolio,
            resolved_role=portfolio_grant.role or CompanyRoleEnum.contributor,
            resolved_status=portfolio_grant.status,
            membership_id=None,
            all_sources=all_sources,
        )
    
    return ResolvedAccess(
        has_access=False,
        access_source=ResolvedAccessSource.direct_project,
        resolved_role=CompanyRoleEnum.contributor,
        resolved_status=MembershipStatusEnum.disabled,
        membership_id=None,
    )


@dataclass
class WorkspaceAccessResult:
    """Result of workspace access resolution."""
    use_portfolio: bool
    portfolio_role: Optional[CompanyRoleEnum] = None
    company_access: Optional[Dict[int, ResolvedAccess]] = None


def resolve_workspace_access(
    portfolio_grants: List[AccessGrant],
    direct_company_grants: List[AccessGrant],
    project_context_grants: List[AccessGrant],
) -> WorkspaceAccessResult:
    """Resolve access to companies for workspace listing.
    
    Returns WorkspaceAccessResult indicating how to display companies.
    
    With hub-scoped portfolio access, users see only companies within their
    accessible portfolio hubs. The portfolio_grants parameter now contains
    hub-specific grants rather than a single global grant.
    
    Otherwise, shows direct company grants and project context companies.
    """
    active_portfolio_grants = [g for g in portfolio_grants if g.status == MembershipStatusEnum.active]
    if active_portfolio_grants:
        return WorkspaceAccessResult(
            use_portfolio=True,
            portfolio_role=active_portfolio_grants[0].role,
        )
    
    result: Dict[int, ResolvedAccess] = {}
    
    for grant in direct_company_grants:
        if grant.membership_id:
            result[grant.membership_id] = ResolvedAccess(
                has_access=grant.status == MembershipStatusEnum.active,
                access_source=grant.source,
                resolved_role=grant.role or CompanyRoleEnum.contributor,
                resolved_status=grant.status,
                membership_id=grant.membership_id,
            )
    
    for grant in project_context_grants:
        if grant.membership_id and grant.membership_id not in result:
            result[grant.membership_id] = ResolvedAccess(
                has_access=grant.status == MembershipStatusEnum.active,
                access_source=grant.source,
                resolved_role=grant.role or CompanyRoleEnum.contributor,
                resolved_status=grant.status,
                membership_id=grant.membership_id,
            )
    
    return WorkspaceAccessResult(
        use_portfolio=False,
        company_access=result,
    )
