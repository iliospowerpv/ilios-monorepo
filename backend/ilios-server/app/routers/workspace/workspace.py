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
                    access_source="membership",
                    project_count=project_count
                ))
                company_ids_seen.add(membership.company_id)
        
        for company in current_user.companies:
            if company.id not in company_ids_seen:
                project_count = db_session.query(Site).filter_by(company_id=company.id).count()
                companies_data.append(UserCompanySchema(
                    company_id=company.id,
                    company_name=company.name,
                    role=None,
                    access_source="project",
                    project_count=project_count
                ))
                company_ids_seen.add(company.id)
        
        if current_user.parent_company and current_user.parent_company.id not in company_ids_seen:
            project_count = db_session.query(Site).filter_by(company_id=current_user.parent_company.id).count()
            companies_data.append(UserCompanySchema(
                company_id=current_user.parent_company.id,
                company_name=current_user.parent_company.name,
                role=None,
                access_source="parent_company",
                project_count=project_count
            ))
            company_ids_seen.add(current_user.parent_company.id)
        
        summary = WorkspaceSummarySchema(
            companies_count=len(companies_data),
            projects_count=len(current_user.sites) if current_user.sites else 0,
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
    description="Returns all users who are members of the specified company.",
)
async def get_company_members(
    company_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> List[CompanyMemberSchema]:
    """Get all members of a company."""
    from app.models.user import User
    
    crud = UserCompanyAccessCRUD(db_session)
    
    if not current_user.is_system_user and not crud.has_company_access(current_user.id, company_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this company"
        )
    
    memberships = crud.get_memberships_by_company(company_id)
    
    members = []
    for m in memberships:
        user = db_session.query(User).get(m.user_id)
        if user:
            members.append(CompanyMemberSchema(
                membership_id=m.id,
                user_id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=CompanyRoleEnum(m.role.value) if m.role else CompanyRoleEnum.contributor,
                status=MembershipStatusEnum(m.status.value) if m.status else MembershipStatusEnum.active,
                access_source="membership"
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
    "/portfolio/members",
    response_model=PortfolioMembersListSchema,
    summary="Get all portfolio-level users",
    description="Returns all users who have portfolio-level access.",
)
async def get_portfolio_members(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> PortfolioMembersListSchema:
    """Get all users with portfolio-level access."""
    from app.models.user import User
    
    if not current_user.is_system_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can view portfolio members"
        )
    
    crud = UserPortfolioAccessCRUD(db_session)
    access_list = crud.get_all_portfolio_users()
    
    members = []
    for access in access_list:
        user = db_session.query(User).get(access.user_id)
        if user:
            members.append(PortfolioMemberSchema(
                access_id=access.id,
                user_id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=CompanyRoleEnum(access.role.value) if access.role else CompanyRoleEnum.contributor,
                status=MembershipStatusEnum(access.status.value) if access.status else MembershipStatusEnum.active,
            ))
    
    return PortfolioMembersListSchema(members=members, total=len(members))


@workspace_router.post(
    "/portfolio/members",
    response_model=UserPortfolioAccessSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user to portfolio level",
    description="Grant a user portfolio-level access, giving them access to all companies.",
)
async def add_portfolio_member(
    payload: UserPortfolioAccessCreate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> UserPortfolioAccessSchema:
    """Add a user to portfolio level (grants access to all companies)."""
    if not current_user.is_system_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators can add portfolio members"
        )
    
    portfolio_crud = UserPortfolioAccessCRUD(db_session)
    company_crud = UserCompanyAccessCRUD(db_session)
    
    existing = portfolio_crud.get_by_user(payload.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has portfolio-level access"
        )
    
    portfolio_access = portfolio_crud.add_portfolio_access(
        user_id=payload.user_id,
        role=CompanyRole(payload.role.value),
        status=MembershipStatus.active,
        created_by_user_id=current_user.id
    )
    
    all_companies = db_session.query(Company).all()
    for company in all_companies:
        existing_company_access = company_crud.get_by_user_and_company(payload.user_id, company.id)
        if not existing_company_access:
            company_crud.add_membership(
                user_id=payload.user_id,
                company_id=company.id,
                role=CompanyRole(payload.role.value),
                status=MembershipStatus.active,
                created_by_user_id=current_user.id,
                created_from_portfolio=True
            )
    
    return UserPortfolioAccessSchema(
        id=portfolio_access.id,
        user_id=portfolio_access.user_id,
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
    description="Remove a user's portfolio-level access and all auto-created company access records.",
)
async def remove_portfolio_member(
    access_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Remove portfolio-level access for a user and clean up company access records."""
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
    
    user_id = access.user_id
    
    portfolio_crud.delete_by_id(access_id)
    
    company_crud = UserCompanyAccessCRUD(db_session)
    portfolio_memberships = company_crud.get_portfolio_memberships_by_user(user_id)
    for membership in portfolio_memberships:
        company_crud.delete_by_id(membership.id)
    
    return None


@workspace_router.get(
    "/projects/{project_id}/members",
    response_model=ProjectMembersListSchema,
    summary="Get members of a project",
    description="Returns all users who are members of the specified project.",
)
async def get_project_members(
    project_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> ProjectMembersListSchema:
    """Get all members of a project."""
    from app.models.user import User
    
    project = db_session.query(Site).get(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project_crud = UserProjectCRUD(db_session)
    company_crud = UserCompanyAccessCRUD(db_session)
    
    if not current_user.is_system_user:
        has_project_access = project_crud.has_project_access(current_user.id, project_id)
        has_company_access = company_crud.has_company_access(current_user.id, project.company_id)
        if not has_project_access and not has_company_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
    
    memberships = project_crud.get_memberships_by_site(project_id)
    
    members = []
    for m in memberships:
        user = db_session.query(User).get(m.user_id)
        if user:
            members.append(ProjectMemberSchema(
                membership_id=m.id,
                user_id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=CompanyRoleEnum(m.role.value) if m.role else CompanyRoleEnum.contributor,
                status=MembershipStatusEnum(m.status.value) if m.status else MembershipStatusEnum.active,
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
