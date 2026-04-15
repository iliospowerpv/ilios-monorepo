"""Place of /account views."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.crud.user import UserCRUD
from app.crud.user_invitation import UserInvitationCRUD
from app.crud.user_password_recovery import UserPasswordRecoveryCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user, get_password_hash
from app.helpers.authorization.custom.diligence_overview_page import DiligenceOverviewPagePermissions
from app.helpers.email import EmailTokenValidator, EmailUtility
from app.helpers.password_recovery_handler import UserPasswordRecoveryHandler
from app.schema.account import PasswordCreationSuccess, PasswordSetupPayload
from app.schema.accessible_entities import (
    AccessibleCompanySchema,
    AccessibleEntitiesResponse,
    AccessibleProjectSchema,
)
from app.schema.auth_token import ResetPasswordSchema
from app.schema.message import Success
from app.schema.user import AccountMgmtModeEnum, CurrentUserSchema, InvitationTokenValidationSuccess, MyUserSchema
from app.static import HTTP_400_RESPONSE, HTTP_410_RESPONSE
from app.static.messages import AccountMessages, UserAccountMessages

account_router = APIRouter()

logger = logging.getLogger(__name__)

MAP_OF_CRUD_HANDLERS_BY_MODE = {
    "sign-up": UserInvitationCRUD,
    "recovery": UserPasswordRecoveryCRUD,
}


@account_router.get(
    "/me",
    response_model=MyUserSchema,
)
async def my_user(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
):
    # define if user has permission for the Diligence Overview page access
    # set it as false by default
    try:
        DiligenceOverviewPagePermissions()(current_user)
        # set it as True if user passes the validation
        diligence_overview_access = True
    except HTTPException:
        diligence_overview_access = False
    current_user.diligence_overview_access = diligence_overview_access
    return current_user


@account_router.get(
    "/email-token",
    response_model=InvitationTokenValidationSuccess,
    responses={
        **HTTP_400_RESPONSE(message=AccountMessages.link_deactivated),
        **HTTP_410_RESPONSE(message=AccountMessages.link_expired),
    },
)
async def email_token_validation(
    email: EmailStr,
    token: str,
    mode: AccountMgmtModeEnum,
    db_session: Session = Depends(get_session),
):
    db_access_layer = MAP_OF_CRUD_HANDLERS_BY_MODE[mode]
    user_password_deeplink = db_access_layer(db_session).get_by_token(token)
    EmailTokenValidator.validate(email, token, user_password_deeplink)
    return {"code": status.HTTP_200_OK, "message": "Token is valid"}


@account_router.post(
    "/password-setup",
    response_model=PasswordCreationSuccess,
    responses={
        **HTTP_400_RESPONSE(message=AccountMessages.link_deactivated),
        **HTTP_410_RESPONSE(message=AccountMessages.link_expired),
    },
)
async def password_setup(
    payload: PasswordSetupPayload,
    mode: AccountMgmtModeEnum,
    db_session: Session = Depends(get_session),
):
    token, password = payload.token, payload.password
    db_access_layer = MAP_OF_CRUD_HANDLERS_BY_MODE[mode]
    user_password_deeplink = db_access_layer(db_session).get_by_token(token)

    EmailTokenValidator.validate(payload.email, token, user_password_deeplink)

    user = user_password_deeplink.user
    user.hashed_password = get_password_hash(password)
    user.is_registered = True
    db_session.delete(user_password_deeplink)

    db_session.commit()

    return {"code": status.HTTP_200_OK, "message": "Password has been set successfully"}


@account_router.post(
    "/password-recovery",
    response_model=Success,
    responses={
        **HTTP_400_RESPONSE(message=UserAccountMessages.account_not_exists),
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "content": {
                "application/json": {
                    "example": {
                        "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "message": UserAccountMessages.account_not_setup,
                    }
                }
            },
        },
        status.HTTP_200_OK: {
            "content": {
                "application/json": {
                    "example": {"code": status.HTTP_200_OK, "message": "Email with password reset instructions was sent"}
                }
            },
        },
    },
)
async def password_recovery(reset_data: ResetPasswordSchema, db_session: Session = Depends(get_session)):
    user = UserCRUD(db_session).get_by_email(reset_data.email)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, UserAccountMessages.account_not_exists)
    if not user.is_registered:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, UserAccountMessages.account_not_setup)

    password_reset_handler = UserPasswordRecoveryHandler(db_session=db_session, user=user)
    password_reset_handler.update_password_recovery_object()
    email_sending_error = EmailUtility().send_password_recovery_email(recipient=user, token=password_reset_handler.token)
    if email_sending_error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The reset password email could not be send. Please try again.",
        )
    return {"code": status.HTTP_200_OK, "message": "Email with password reset instructions was sent"}


@account_router.get(
    "/me/accessible-entities",
    response_model=AccessibleEntitiesResponse,
    summary="Get accessible companies and projects for context bar",
    description="Returns all companies and projects the current user has access to, "
                "based on UserCompanyAccess memberships, UserProject assignments, portfolio hub access, and parent_company_id. "
                "System users get all companies and projects.",
)
async def get_accessible_entities(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> AccessibleEntitiesResponse:
    from app.models.company import Company
    from app.models.site import Site
    from app.models.user import UserCompanyAccess, UserPortfolioAccess, MembershipStatus
    from app.crud.user_portfolio_access import UserPortfolioAccessCRUD
    
    companies: list[AccessibleCompanySchema] = []
    projects: list[AccessibleProjectSchema] = []
    
    if current_user.is_system_user:
        all_companies = db_session.query(Company).filter(
            Company.is_archived == False
        ).order_by(Company.name).all()
        all_sites = db_session.query(Site).join(Company).filter(
            Site.is_archived == False,
            Company.is_archived == False
        ).order_by(Company.name, Site.name).all()
        
        companies = [
            AccessibleCompanySchema(id=c.id, name=c.name)
            for c in all_companies
        ]
        
        projects = [
            AccessibleProjectSchema(
                id=s.id,
                name=s.name,
                company_id=s.company_id,
                company_name=s.company.name if s.company else "Unknown"
            )
            for s in all_sites
        ]
    else:
        company_ids_seen = set()
        project_ids_seen = set()
        
        portfolio_crud = UserPortfolioAccessCRUD(db_session)
        user_hub_ids = portfolio_crud.get_user_hub_ids(current_user.id)
        
        if user_hub_ids:
            hub_companies = db_session.query(Company).filter(
                Company.is_archived == False,
                (Company.portfolio_hub_id.in_(user_hub_ids)) | (Company.id.in_(user_hub_ids))
            ).order_by(Company.name).all()
            
            for company in hub_companies:
                if company.id not in company_ids_seen:
                    companies.append(AccessibleCompanySchema(id=company.id, name=company.name))
                    company_ids_seen.add(company.id)
            
            hub_sites = db_session.query(Site).filter(
                Site.is_archived == False,
                Site.company_id.in_([c.id for c in hub_companies])
            ).all()
            for site in hub_sites:
                if site.id not in project_ids_seen:
                    projects.append(AccessibleProjectSchema(
                        id=site.id,
                        name=site.name,
                        company_id=site.company_id,
                        company_name=site.company.name if site.company else "Unknown"
                    ))
                    project_ids_seen.add(site.id)
        
        company_memberships = db_session.query(UserCompanyAccess).filter(
            UserCompanyAccess.user_id == current_user.id,
            UserCompanyAccess.status == MembershipStatus.active
        ).all()
        
        for membership in company_memberships:
            if membership.company and not membership.company.is_archived and membership.company_id not in company_ids_seen:
                companies.append(AccessibleCompanySchema(
                    id=membership.company.id,
                    name=membership.company.name
                ))
                company_ids_seen.add(membership.company_id)
        
        for company in current_user.companies:
            if company.id not in company_ids_seen and not getattr(company, 'is_archived', False):
                companies.append(AccessibleCompanySchema(id=company.id, name=company.name))
                company_ids_seen.add(company.id)
        
        if current_user.parent_company and current_user.parent_company.id not in company_ids_seen and not getattr(current_user.parent_company, 'is_archived', False):
            companies.append(AccessibleCompanySchema(
                id=current_user.parent_company.id,
                name=current_user.parent_company.name
            ))
            company_ids_seen.add(current_user.parent_company.id)
        
        for site in current_user.sites:
            if site.id not in project_ids_seen and not getattr(site, 'is_archived', False):
                projects.append(AccessibleProjectSchema(
                    id=site.id,
                    name=site.name,
                    company_id=site.company_id,
                    company_name=site.company.name if site.company else "Unknown"
                ))
                project_ids_seen.add(site.id)
    
    companies.sort(key=lambda c: c.name.lower())
    projects.sort(key=lambda p: (p.company_name.lower(), p.name.lower()))
    
    return AccessibleEntitiesResponse(companies=companies, projects=projects)
