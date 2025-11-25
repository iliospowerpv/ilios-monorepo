"""Contractors is representation of companies for Settings (Admin) module"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.base_crud import UniqueConstraintViolationError
from app.crud.company import CompanyCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.helpers.authorization import AuthorizedUser, SettingsPermissions, get_current_admin_user
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.helpers.task_tracker.board_defaults_helper import create_default_board
from app.models.board import BoardModuleEnum, BoardRelatedEntityTypeEnum
from app.schema.company import (
    CompanyCreationSuccess,
    CompanyUpdateSuccess,
    ContractorsOrderByFieldEnum,
    ContractorsPaginator,
    CreateCompanySchema,
    UpsertCompanySchema,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, HTTP_409_RESPONSE, CompanyMessages, PermissionsActions

logger = logging.getLogger(__name__)
contractors_router = APIRouter()


@contractors_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=CompanyCreationSuccess,
    responses={**HTTP_409_RESPONSE(message=CompanyMessages.company_already_exists)},
    dependencies=[Depends(get_current_admin_user)],
)
async def create(
    company: CreateCompanySchema,
    db_session: Session = Depends(get_session),
):
    try:
        company_data = CompanyCRUD(db_session).create_item(company.model_dump())
    except UniqueConstraintViolationError:
        logger.exception(message := CompanyMessages.company_already_exists)
        raise HTTPException(status.HTTP_409_CONFLICT, message)
    logger.info(f"Created company with id {company_data.id}")
    # Create asset default company board
    create_default_board(company_data.id, BoardRelatedEntityTypeEnum.company, db_session, module=BoardModuleEnum.asset)
    # Create O&M default company board
    create_default_board(company_data.id, BoardRelatedEntityTypeEnum.company, db_session, module=BoardModuleEnum.om)
    return {"code": status.HTTP_201_CREATED, "message": "Company has been successfully created"}


@contractors_router.get("/", response_model=ContractorsPaginator, dependencies=[Depends(get_current_admin_user)])
async def get(
    search: str | None = None,
    query_params: tuple = Depends(validate_query_params(order_by=ContractorsOrderByFieldEnum)),
    *,
    db_session: Session = Depends(get_session),
):
    company_crud = CompanyCRUD(db_session)
    skip, limit, order_by, order_direction = query_params
    total, companies = company_crud.filter(search, skip, limit, order_by, order_direction)
    return {"items": companies, **pagination_details(skip, limit, total)}


@contractors_router.get(
    "/{company_id}",
    response_model=CreateCompanySchema,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(get_current_admin_user)],
)
async def get_by_id(
    company_id: int,
    db_session: Session = Depends(get_session),
):
    company = CompanyCRUD(db_session).get_by_id(company_id)
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return company


@contractors_router.put(
    "/{company_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CompanyUpdateSuccess,
    responses={**HTTP_409_RESPONSE(message=CompanyMessages.company_already_exists)},
)
async def update(
    company_id: int,
    company: UpsertCompanySchema,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
    db_session: Session = Depends(get_session),
):
    # Company Admin should be able to edit only parent company
    if current_user.parent_company_id and current_user.parent_company_id != company_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN)

    try:
        updated_count = CompanyCRUD(db_session).update_by_id(company_id, company.model_dump())
    except UniqueConstraintViolationError:
        logger.exception(message := CompanyMessages.company_already_exists)
        raise HTTPException(status.HTTP_409_CONFLICT, message)

    if not updated_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return {"code": status.HTTP_202_ACCEPTED, "message": "Company has been updated successfully"}


@contractors_router.delete(
    "/{company_id}/internal",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def delete(company_id: int, db_session: Session = Depends(get_session)):
    deleted_count = CompanyCRUD(db_session).delete_by_id(company_id)
    if deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
