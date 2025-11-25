import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.alert import AlertCRUD
from app.crud.device import DeviceCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import AuthorizedUser, OnMPermissions
from app.helpers.authorization.project_access import get_authorized_alert, get_authorized_company, get_authorized_site
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.models.alert import Alert
from app.models.company import Company
from app.models.site import Site
from app.schema.alert import (
    AlertEditSuccess,
    CompanyAlertsOrderByFieldEnum,
    CompanyAlertsPaginator,
    DeviceAlertsOrderByFieldEnum,
    DeviceAlertsPaginator,
    SiteAlertsOrderByFieldEnum,
    SiteAlertsPaginator,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_404_RESPONSE, AlertMessages, PermissionsActions

logger = logging.getLogger(__name__)
alerts_router = APIRouter()


@alerts_router.get(
    "/devices/{device_id}",
    response_model=DeviceAlertsPaginator,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
)
async def get_device_alerts(
    device_id: int,
    *,
    is_resolved: Annotated[bool | None, Query(enum=(True, False))] = None,
    query_params: tuple = Depends(validate_query_params(order_by=DeviceAlertsOrderByFieldEnum)),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Fetch paginated alerts of requested device if current user has access to the device's site"""
    device = DeviceCRUD(db_session).get_by_id(device_id)
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    site_id = device.site_id
    get_authorized_site(site_id, current_user, db_session)

    skip, limit, order_by, order_direction = query_params
    total, alerts = AlertCRUD(db_session).get_by_target_entity_id(
        device_id,
        site_id,
        is_resolved=is_resolved,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )
    return {"items": alerts, **pagination_details(skip, limit, total)}


@alerts_router.get(
    "/sites/{site_id}",
    response_model=SiteAlertsPaginator,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
)
async def get_site_alerts(
    is_resolved: Annotated[bool | None, Query(enum=(True, False))] = None,
    site: Site = Depends(get_authorized_site),
    query_params: tuple = Depends(validate_query_params(order_by=SiteAlertsOrderByFieldEnum)),
    db_session: Session = Depends(get_session),
):
    """Fetch paginated alerts of requested site if current user has access to it"""
    skip, limit, order_by, order_direction = query_params
    total, alerts = AlertCRUD(db_session).get_by_target_entity_id(
        site_id=site.id,
        is_resolved=is_resolved,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )
    return {"items": alerts, **pagination_details(skip, limit, total)}


@alerts_router.get(
    "/companies/{company_id}",
    response_model=CompanyAlertsPaginator,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
)
async def get_company_alerts(
    company: Company = Depends(get_authorized_company),
    *,
    is_resolved: Annotated[bool | None, Query(enum=(True, False))] = None,
    query_params: tuple = Depends(validate_query_params(order_by=CompanyAlertsOrderByFieldEnum)),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Fetch paginated alerts of requested company if current user has access to it"""

    skip, limit, order_by, order_direction = query_params
    total, alerts = AlertCRUD(db_session).get_by_target_entity_id(
        company_id=company.id,
        is_resolved=is_resolved,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
        # on the company level, we need to ensure we return only alerts for sites user has access to
        site_ids_to_limit=current_user.get_limited_sites_ids(),
    )
    return {"items": alerts, **pagination_details(skip, limit, total)}


@alerts_router.put(
    "/{alert_id}/resolve",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AlertEditSuccess,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(OnMPermissions(PermissionsActions.edit)))],
)
async def resolve_alert(
    alert_obj: Alert = Depends(get_authorized_alert),
    db_session: Session = Depends(get_session),
):
    """Resolve alert if current user has access to the device's site"""

    alert_obj.is_resolved = True
    alert_obj.alert_end = datetime.now(timezone.utc)
    db_session.commit()

    return {"code": status.HTTP_202_ACCEPTED, "message": AlertMessages.alert_update_success}
