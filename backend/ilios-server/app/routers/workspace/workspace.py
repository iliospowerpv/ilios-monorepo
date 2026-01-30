"""Workspace API endpoints - user-centric landing and company management."""

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.user_company_access import UserCompanyAccessCRUD
from app.crud.user_portfolio_access import UserPortfolioAccessCRUD
from app.crud.user_project import UserProjectCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.models.company import Company
from app.models.site import Site
from app.models.user import UserCompanyAccess, UserPortfolioAccess, UserProject, CompanyRole, MembershipStatus
from app.schema.user import CurrentUserSchema
from app.schema.user_company_access import (
    CompanyMemberSchema,
    CompanyRoleEnum,
    MembershipStatusEnum,
    UserCompanyAccessCreate,
    UserCompanyAccessSchema,
    UserCompanyAccessUpdate,
    UserCompanySchema,
    WorkspaceResponseSchema,
    WorkspaceSummarySchema,
)
from app.schema.user_portfolio_access import (
    AvailableHubsSchema,
    PortfolioHubSchema,
    PortfolioMemberSchema,
    PortfolioMembersListSchema,
    UserPortfolioAccessCreate,
    UserPortfolioAccessSchema,
    UserPortfolioAccessUpdate,
)
from app.schema.user_project_access import (
    ProjectMemberSchema,
    ProjectMembersListSchema,
    UserProjectAccessCreate,
    UserProjectAccessSchema,
    UserProjectAccessUpdate,
)

workspace_router = APIRouter()
logger = logging.getLogger(__name__)


@workspace_router.get(
    "",
    response_model=WorkspaceResponseSchema,
    summary="Get workspace data for current user",
    description="Returns summary statistics and lists of accessible companies and projects.",
)
async def get_workspace(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> WorkspaceResponseSchema:
    """Get workspace data for the current user."""
    
    company_ids_seen = set()
    companies_data: List[UserCompanySchema] = []
    
    if current_user.is_system_user:
        all_companies = db_session.query(Company).order_by(Company.name).all()
        all_projects_count = db_session.query(Site).count()
        
        for c in all_companies:
            project_count = db_session.query(Site).filter_by(company_id=c.id).count()
            companies_data.append(UserCompanySchema(
                company_id=c.id,
                company_name=c.name,
                role=CompanyRoleEnum.company_admin,
                access_source="system_admin",
                project_count=project_count
            ))
        
        summary = WorkspaceSummarySchema(
            companies_count=len(all_companies),
            projects_count=all_projects_count,
            pending_tasks_count=0,
            needs_attention_count=0
        )
    else:
        from app.helpers.portfolio_hub import resolve_company_hub_id
        
        portfolio_crud = UserPortfolioAccessCRUD(db_session)
        project_crud = UserProjectCRUD(db_session)
        
        user_hub_ids = portfolio_crud.get_user_hub_ids(current_user.id)
        if user_hub_ids:
            portfolio_companies = db_session.query(Company).filter(
                (Company.portfolio_hub_id.in_(user_hub_ids)) | (Company.id.in_(user_hub_ids))
            ).order_by(Company.name).all()
            
            portfolio_accesses = {
                a.portfolio_hub_company_id: a 
                for a in portfolio_crud.get_all_by_user(current_user.id, status=MembershipStatus.active)
            }
            
            for c in portfolio_companies:
                if c.id not in company_ids_seen:
                    hub_id = resolve_company_hub_id(db_session, c.id)
                    portfolio_access = portfolio_accesses.get(hub_id)
                    project_count = db_session.query(Site).filter_by(company_id=c.id).count()
                    companies_data.append(UserCompanySchema(
                        company_id=c.id,
                        company_name=c.name,
                        role=CompanyRoleEnum(portfolio_access.role.value) if portfolio_access and portfolio_access.role else None,
                        access_source="inherited_portfolio",
                        project_count=project_count
                    ))
                    company_ids_seen.add(c.id)
        
        if True:
            company_memberships = db_session.query(UserCompanyAccess).filter(
                UserCompanyAccess.user_id == current_user.id,
                UserCompanyAccess.status == MembershipStatus.active
            ).all()
            
            for membership in company_memberships:
                if membership.company and membership.company_id not in company_ids_seen:
                    project_count = db_session.query(Site).filter_by(company_id=membership.company_id).count()
                    companies_data.append(UserCompanySchema(
                        company_id=membership.company.id,
                        company_name=membership.company.name,
                        role=CompanyRoleEnum(membership.role.value) if membership.role else None,
                        access_source="direct_company",
                        project_count=project_count
                    ))
                    company_ids_seen.add(membership.company_id)
            
            project_memberships = project_crud.get_memberships_by_user(
                user_id=current_user.id,
                status=MembershipStatus.active
            )
            for pm in project_memberships:
                site = db_session.query(Site).get(pm.site_id)
                if site and site.company_id not in company_ids_seen:
                    company = db_session.query(Company).get(site.company_id)
                    if company:
                        project_count = db_session.query(Site).filter_by(company_id=company.id).count()
                        companies_data.append(UserCompanySchema(
                            company_id=company.id,
                            company_name=company.name,
                            role=CompanyRoleEnum(pm.role.value) if pm.role else None,
                            access_source="project_context",
                            project_count=project_count
                        ))
                        company_ids_seen.add(company.id)
        
        total_projects = 0
        for company in companies_data:
            total_projects += company.project_count
        
        summary = WorkspaceSummarySchema(
            companies_count=len(companies_data),
            projects_count=total_projects,
            pending_tasks_count=0,
            needs_attention_count=0
        )
    
    companies_data.sort(key=lambda c: c.company_name.lower())
    
    return WorkspaceResponseSchema(
        summary=summary,
        companies=companies_data
    )


@workspace_router.get(
    "/companies/{company_id}/members",
    response_model=List[CompanyMemberSchema],
    summary="Get members of a company",
    description="Returns all users who have access to the company (direct and inherited).",
)
async def get_company_members(
    company_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> List[CompanyMemberSchema]:
    """Get all members of a company including computed inherited access.
    
    Uses centralized access resolution for consistent precedence and status blocking.
    """
    from app.models.user import User
    from app.schema.user_company_access import AccessSourceEnum
    from app.helpers.access_resolution import (
        AccessGrant, ResolvedAccessSource, resolve_company_access
    )
    
    company_crud = UserCompanyAccessCRUD(db_session)
    portfolio_crud = UserPortfolioAccessCRUD(db_session)
    project_crud = UserProjectCRUD(db_session)
    
    has_portfolio_access = portfolio_crud.get_by_user(current_user.id) is not None
    has_company_access = company_crud.has_company_access(current_user.id, company_id)
    
    if not current_user.is_system_user and not has_company_access and not has_portfolio_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this company"
        )
    
    direct_by_user = {}
    direct_memberships = company_crud.get_memberships_by_company(company_id)
    for m in direct_memberships:
        direct_role = CompanyRoleEnum(m.role.value) if m.role else CompanyRoleEnum.contributor
        direct_status = MembershipStatusEnum(m.status.value) if m.status else MembershipStatusEnum.active
        direct_by_user[m.user_id] = AccessGrant(
            source=ResolvedAccessSource.direct_company,
            role=direct_role,
            status=direct_status,
            membership_id=m.id,
        )
    
    portfolio_by_user = {}
    portfolio_users = portfolio_crud.get_all_portfolio_users()
    for p in portfolio_users:
        inherited_role = CompanyRoleEnum(p.role.value) if p.role else CompanyRoleEnum.contributor
        inherited_status = MembershipStatusEnum(p.status.value) if p.status else MembershipStatusEnum.active
        portfolio_by_user[p.user_id] = AccessGrant(
            source=ResolvedAccessSource.inherited_portfolio,
            role=inherited_role,
            status=inherited_status,
            membership_id=None,
        )
    
    project_only_by_user = {}
    project_memberships = project_crud.get_memberships_by_site(company_id=company_id)
    for pm in project_memberships:
        project_role = CompanyRoleEnum(pm.role.value) if pm.role else CompanyRoleEnum.contributor
        project_status = MembershipStatusEnum(pm.status.value) if pm.status else MembershipStatusEnum.active
        if pm.user_id not in project_only_by_user:
            project_only_by_user[pm.user_id] = AccessGrant(
                source=ResolvedAccessSource.project_only,
                role=project_role,
                status=project_status,
                membership_id=None,
            )
    
    all_user_ids = set(direct_by_user.keys()) | set(portfolio_by_user.keys()) | set(project_only_by_user.keys())
    
    members = []
    for user_id in all_user_ids:
        user = db_session.query(User).get(user_id)
        if not user:
            continue
        
        resolved = resolve_company_access(
            direct_grant=direct_by_user.get(user_id),
            portfolio_grant=portfolio_by_user.get(user_id),
            project_only_grant=project_only_by_user.get(user_id),
        )
        
        access_source_map = {
            ResolvedAccessSource.direct_company: AccessSourceEnum.direct_company,
            ResolvedAccessSource.inherited_portfolio: AccessSourceEnum.inherited_portfolio,
            ResolvedAccessSource.project_only: AccessSourceEnum.project_only,
        }
        
        members.append(CompanyMemberSchema(
            membership_id=resolved.membership_id,
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            access_source=access_source_map.get(resolved.access_source, AccessSourceEnum.direct_company),
            resolved_role=resolved.resolved_role,
            resolved_status=resolved.resolved_status,
            direct_role=resolved.direct_role,
            inherited_role=resolved.inherited_role,
        ))
    
    return members


@workspace_router.post(
    "/companies/{company_id}/members",
    response_model=UserCompanyAccessSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to a company",
    description="Add a user as a member of a company with a specific role.",
)
async def add_company_member(
    company_id: int,
    payload: UserCompanyAccessCreate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> UserCompanyAccessSchema:
    """Add a user to a company."""
    crud = UserCompanyAccessCRUD(db_session)
    
    if not current_user.is_system_user and not crud.is_company_admin(current_user.id, company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can add members"
        )
    
    existing = crud.get_by_user_and_company(payload.user_id, company_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this company"
        )
    
    membership = crud.add_membership(
        user_id=payload.user_id,
        company_id=company_id,
        role=CompanyRole(payload.role.value),
        status=MembershipStatus.active,
        created_by_user_id=current_user.id
    )
    
    return UserCompanyAccessSchema(
        id=membership.id,
        user_id=membership.user_id,
        company_id=membership.company_id,
        role=CompanyRoleEnum(membership.role.value) if membership.role else CompanyRoleEnum.contributor,
        status=MembershipStatusEnum(membership.status.value) if membership.status else MembershipStatusEnum.active,
        created_at=membership.created_at,
        created_by_user_id=membership.created_by_user_id,
        updated_at=membership.updated_at
    )


@workspace_router.patch(
    "/companies/{company_id}/members/{membership_id}",
    response_model=UserCompanyAccessSchema,
    summary="Update a company membership",
    description="Update a user's role or status within a company.",
)
async def update_company_member(
    company_id: int,
    membership_id: int,
    payload: UserCompanyAccessUpdate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> UserCompanyAccessSchema:
    """Update a company membership."""
    crud = UserCompanyAccessCRUD(db_session)
    
    if not current_user.is_system_user and not crud.is_company_admin(current_user.id, company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can update memberships"
        )
    
    membership = crud.get_by_id(membership_id)
    if not membership or membership.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )
    
    update_data = {}
    if payload.role is not None:
        update_data["role"] = CompanyRole(payload.role.value)
    if payload.status is not None:
        update_data["status"] = MembershipStatus(payload.status.value)
    
    if update_data:
        crud.update_by_id(membership_id, update_data)
        membership = crud.get_by_id(membership_id)
    
    return UserCompanyAccessSchema(
        id=membership.id,
        user_id=membership.user_id,
        company_id=membership.company_id,
        role=CompanyRoleEnum(membership.role.value) if membership.role else CompanyRoleEnum.contributor,
        status=MembershipStatusEnum(membership.status.value) if membership.status else MembershipStatusEnum.active,
        created_at=membership.created_at,
        created_by_user_id=membership.created_by_user_id,
        updated_at=membership.updated_at
    )


@workspace_router.delete(
    "/companies/{company_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a company membership",
    description="Remove a user's membership from a company.",
)
async def remove_company_member(
    company_id: int,
    membership_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Remove a company membership."""
    crud = UserCompanyAccessCRUD(db_session)
    
    if not current_user.is_system_user and not crud.is_company_admin(current_user.id, company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only company admins can remove memberships"
        )
    
    membership = crud.get_by_id(membership_id)
    if not membership or membership.company_id != company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )
    
    crud.delete_by_id(membership_id)
    return None


@workspace_router.get(
    "/portfolio/hubs",
    response_model=AvailableHubsSchema,
    summary="Get available portfolio hubs",
    description="Returns all portfolio hubs (companies that serve as hub roots) with counts of companies in each.",
)
async def get_portfolio_hubs(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AvailableHubsSchema:
    """Get all available portfolio hubs for granting access."""
    if not current_user.is_system_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can view portfolio hubs"
        )
    
    hub_companies = db_session.query(Company).filter(
        (Company.portfolio_hub_id == None) | (Company.portfolio_hub_id == Company.id)
    ).order_by(Company.name).all()
    
    hubs = []
    for hub in hub_companies:
        companies_count = db_session.query(Company).filter(
            (Company.portfolio_hub_id == hub.id) | (Company.id == hub.id)
        ).count()
        hubs.append(PortfolioHubSchema(
            hub_company_id=hub.id,
            hub_company_name=hub.name,
            companies_count=companies_count,
        ))
    
    return AvailableHubsSchema(hubs=hubs)


@workspace_router.get(
    "/portfolio/members",
    response_model=PortfolioMembersListSchema,
    summary="Get all portfolio-level users",
    description="Returns all users who have portfolio-level access. Optionally filter by hub.",
)
async def get_portfolio_members(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    hub_company_id: Optional[int] = None,
) -> PortfolioMembersListSchema:
    """Get all users with portfolio-level access, optionally filtered by hub."""
    from app.models.user import User
    
    if not current_user.is_system_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can view portfolio members"
        )
    
    crud = UserPortfolioAccessCRUD(db_session)
    access_list = crud.get_all_portfolio_users(hub_company_id=hub_company_id)
    
    members = []
    for access in access_list:
        user = db_session.query(User).get(access.user_id)
        hub_company = None
        if access.portfolio_hub_company_id:
            hub_company = db_session.query(Company).get(access.portfolio_hub_company_id)
        if user:
            members.append(PortfolioMemberSchema(
                access_id=access.id,
                user_id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=CompanyRoleEnum(access.role.value) if access.role else CompanyRoleEnum.contributor,
                status=MembershipStatusEnum(access.status.value) if access.status else MembershipStatusEnum.active,
                portfolio_hub_company_id=access.portfolio_hub_company_id,
                portfolio_hub_company_name=hub_company.name if hub_company else None,
            ))
    
    return PortfolioMembersListSchema(members=members, total=len(members))


@workspace_router.post(
    "/portfolio/members",
    response_model=UserPortfolioAccessSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to portfolio level",
    description="Grant a user portfolio-level access to a specific portfolio hub.",
)
async def add_portfolio_member(
    payload: UserPortfolioAccessCreate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> UserPortfolioAccessSchema:
    """Add a user to portfolio level (grants access to companies within the hub)."""
    if not current_user.is_system_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can add portfolio members"
        )
    
    hub_company = db_session.query(Company).get(payload.portfolio_hub_company_id)
    if not hub_company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio hub company not found"
        )
    
    portfolio_crud = UserPortfolioAccessCRUD(db_session)
    
    existing = portfolio_crud.get_by_user_and_hub(payload.user_id, payload.portfolio_hub_company_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has portfolio-level access to this hub"
        )
    
    portfolio_access = portfolio_crud.add_portfolio_access(
        user_id=payload.user_id,
        portfolio_hub_company_id=payload.portfolio_hub_company_id,
        role=CompanyRole(payload.role.value),
        status=MembershipStatus.active,
        created_by_user_id=current_user.id
    )
    
    return UserPortfolioAccessSchema(
        id=portfolio_access.id,
        user_id=portfolio_access.user_id,
        portfolio_hub_company_id=portfolio_access.portfolio_hub_company_id,
        role=CompanyRoleEnum(portfolio_access.role.value) if portfolio_access.role else CompanyRoleEnum.contributor,
        status=MembershipStatusEnum(portfolio_access.status.value) if portfolio_access.status else MembershipStatusEnum.active,
        created_at=portfolio_access.created_at,
        created_by_user_id=portfolio_access.created_by_user_id,
        updated_at=portfolio_access.updated_at
    )


@workspace_router.delete(
    "/portfolio/members/{access_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove portfolio-level access",
    description="Remove a user's portfolio-level access. Direct company/project grants are preserved.",
)
async def remove_portfolio_member(
    access_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Remove portfolio-level access for a user. Does not affect direct company/project grants."""
    if not current_user.is_system_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can remove portfolio members"
        )
    
    portfolio_crud = UserPortfolioAccessCRUD(db_session)
    access = portfolio_crud.get_by_id(access_id)
    if not access:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio access not found"
        )
    
    portfolio_crud.delete_by_id(access_id)
    
    return None


@workspace_router.get(
    "/projects/{project_id}/members",
    response_model=ProjectMembersListSchema,
    summary="Get members of a project",
    description="Returns all users who have access to the project (direct and inherited).",
)
async def get_project_members(
    project_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> ProjectMembersListSchema:
    """Get all members of a project including computed inherited access.
    
    Uses centralized access resolution for consistent precedence and status blocking.
    """
    from app.models.user import User
    from app.schema.user_project_access import ProjectAccessSourceEnum
    from app.helpers.access_resolution import (
        AccessGrant, ResolvedAccessSource, resolve_project_access
    )
    
    project = db_session.query(Site).get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project_crud = UserProjectCRUD(db_session)
    company_crud = UserCompanyAccessCRUD(db_session)
    portfolio_crud = UserPortfolioAccessCRUD(db_session)
    
    has_portfolio_access = portfolio_crud.get_by_user(current_user.id) is not None
    has_company_access = company_crud.has_company_access(current_user.id, project.company_id)
    has_project_access = project_crud.has_project_access(current_user.id, project_id)
    
    if not current_user.is_system_user and not has_project_access and not has_company_access and not has_portfolio_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project"
        )
    
    direct_by_user = {}
    direct_memberships = project_crud.get_memberships_by_site(site_id=project_id)
    for m in direct_memberships:
        direct_role = CompanyRoleEnum(m.role.value) if m.role else CompanyRoleEnum.contributor
        direct_status = MembershipStatusEnum(m.status.value) if m.status else MembershipStatusEnum.active
        direct_by_user[m.user_id] = AccessGrant(
            source=ResolvedAccessSource.direct_project,
            role=direct_role,
            status=direct_status,
            membership_id=m.id,
        )
    
    company_by_user = {}
    company_memberships = company_crud.get_memberships_by_company(project.company_id)
    for cm in company_memberships:
        company_role = CompanyRoleEnum(cm.role.value) if cm.role else CompanyRoleEnum.contributor
        company_status = MembershipStatusEnum(cm.status.value) if cm.status else MembershipStatusEnum.active
        company_by_user[cm.user_id] = AccessGrant(
            source=ResolvedAccessSource.inherited_company,
            role=company_role,
            status=company_status,
            membership_id=None,
        )
    
    portfolio_by_user = {}
    portfolio_users = portfolio_crud.get_all_portfolio_users()
    for p in portfolio_users:
        portfolio_role = CompanyRoleEnum(p.role.value) if p.role else CompanyRoleEnum.contributor
        portfolio_status = MembershipStatusEnum(p.status.value) if p.status else MembershipStatusEnum.active
        portfolio_by_user[p.user_id] = AccessGrant(
            source=ResolvedAccessSource.inherited_portfolio,
            role=portfolio_role,
            status=portfolio_status,
            membership_id=None,
        )
    
    all_user_ids = set(direct_by_user.keys()) | set(company_by_user.keys()) | set(portfolio_by_user.keys())
    
    members = []
    for user_id in all_user_ids:
        user = db_session.query(User).get(user_id)
        if not user:
            continue
        
        resolved = resolve_project_access(
            direct_grant=direct_by_user.get(user_id),
            company_grant=company_by_user.get(user_id),
            portfolio_grant=portfolio_by_user.get(user_id),
        )
        
        source_map = {
            ResolvedAccessSource.direct_project: ProjectAccessSourceEnum.direct_project,
            ResolvedAccessSource.inherited_company: ProjectAccessSourceEnum.inherited_company,
            ResolvedAccessSource.inherited_portfolio: ProjectAccessSourceEnum.inherited_portfolio,
        }
        
        members.append(ProjectMemberSchema(
            membership_id=resolved.membership_id,
            user_id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            access_source=source_map.get(resolved.access_source, ProjectAccessSourceEnum.direct_project),
            resolved_role=resolved.resolved_role,
            resolved_status=resolved.resolved_status,
        ))
    
    return ProjectMembersListSchema(members=members, total=len(members))


@workspace_router.post(
    "/projects/{project_id}/members",
    response_model=UserProjectAccessSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to a project",
    description="Add a user as a member of a project with a specific role.",
)
async def add_project_member(
    project_id: int,
    payload: UserProjectAccessCreate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> UserProjectAccessSchema:
    """Add a user to a project."""
    project = db_session.query(Site).get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project_crud = UserProjectCRUD(db_session)
    company_crud = UserCompanyAccessCRUD(db_session)
    
    if not current_user.is_system_user:
        is_company_admin = company_crud.is_company_admin(current_user.id, project.company_id)
        is_project_admin = project_crud.is_project_admin(current_user.id, project_id)
        if not is_company_admin and not is_project_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company or project admins can add members"
            )
    
    existing = project_crud.get_by_user_and_site(payload.user_id, project_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this project"
        )
    
    membership = project_crud.add_membership(
        user_id=payload.user_id,
        site_id=project_id,
        company_id=project.company_id,
        role=CompanyRole(payload.role.value),
        status=MembershipStatus.active,
        created_by_user_id=current_user.id
    )
    
    return UserProjectAccessSchema(
        id=membership.id,
        user_id=membership.user_id,
        site_id=membership.site_id,
        company_id=membership.company_id,
        role=CompanyRoleEnum(membership.role.value) if membership.role else CompanyRoleEnum.contributor,
        status=MembershipStatusEnum(membership.status.value) if membership.status else MembershipStatusEnum.active,
        created_at=membership.created_at,
        created_by_user_id=membership.created_by_user_id,
        updated_at=membership.updated_at
    )


@workspace_router.delete(
    "/projects/{project_id}/members/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a project membership",
    description="Remove a user's membership from a project.",
)
async def remove_project_member(
    project_id: int,
    membership_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Remove a project membership."""
    project = db_session.query(Site).get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project_crud = UserProjectCRUD(db_session)
    company_crud = UserCompanyAccessCRUD(db_session)
    
    if not current_user.is_system_user:
        is_company_admin = company_crud.is_company_admin(current_user.id, project.company_id)
        is_project_admin = project_crud.is_project_admin(current_user.id, project_id)
        if not is_company_admin and not is_project_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company or project admins can remove members"
            )
    
    membership = project_crud.get_by_id(membership_id)
    if not membership or membership.site_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )
    
    project_crud.delete_by_id(membership_id)
    return None


@workspace_router.get(
    "/portfolio/hubs",
    response_model=AvailableHubsSchema,
    summary="Get available portfolio hubs",
    description="Returns all companies that serve as portfolio hubs (for admin hub picker).",
)
async def get_portfolio_hubs(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AvailableHubsSchema:
    """Get all companies that serve as portfolio hubs.
    
    A company is a hub if it's either:
    - Has portfolio_hub_id = NULL (is its own hub)
    - Is referenced by other companies as their portfolio_hub_id
    
    For system admins, returns all potential hubs.
    For regular users, returns hubs they have access to.
    """
    from sqlalchemy import func
    from app.helpers.portfolio_hub import resolve_company_hub_id
    
    if current_user.is_system_user:
        hub_ids_query = db_session.query(Company.id).filter(
            Company.portfolio_hub_id.is_(None)
        ).all()
        hub_ids = {row[0] for row in hub_ids_query}
    else:
        portfolio_crud = UserPortfolioAccessCRUD(db_session)
        hub_ids = portfolio_crud.get_user_hub_ids(current_user.id)
    
    hubs = []
    for hub_id in hub_ids:
        hub_company = db_session.query(Company).get(hub_id)
        if hub_company:
            companies_count = db_session.query(func.count(Company.id)).filter(
                (Company.portfolio_hub_id == hub_id) | (Company.id == hub_id)
            ).scalar()
            hubs.append(PortfolioHubSchema(
                hub_company_id=hub_company.id,
                hub_company_name=hub_company.name,
                companies_count=companies_count or 1
            ))
    
    hubs.sort(key=lambda h: h.hub_company_name.lower())
    return AvailableHubsSchema(hubs=hubs)
