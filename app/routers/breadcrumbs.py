import logging
from typing import Union

from fastapi import APIRouter
from fastapi.params import Depends

from app.helpers.authorization import (
    AssetPermissions,
    AuthorizedUser,
    DiligencePermissions,
    InvestorDashboardPermissions,
    OnMPermissions,
    RoleBasedDashboardPermissions,
    SettingsPermissions,
)
from app.helpers.authorization.entity_based.breadcrumbs import get_authorized_breadcrumbs_entity
from app.models.company import Company
from app.models.device import Device
from app.models.site import Site
from app.models.task import Task
from app.schema.breadcrumbs import BreadcrumbsSchema
from app.static import BreadcrumbsEntityTypes, PermissionsActions, PermissionsModules

logger = logging.getLogger(__name__)
breadcrumbs_router = APIRouter()


@breadcrumbs_router.get(
    "/",
    response_model=BreadcrumbsSchema,
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.view, validate_query_module_name=True),
                    DiligencePermissions(PermissionsActions.view, validate_query_module_name=True),
                    OnMPermissions(PermissionsActions.view, validate_query_module_name=True),
                    InvestorDashboardPermissions(PermissionsActions.view, validate_query_module_name=True),
                    RoleBasedDashboardPermissions(PermissionsActions.view, validate_query_module_name=True),
                    SettingsPermissions(PermissionsActions.view, validate_query_module_name=True),
                ]
            )
        ),
    ],
    description="Return entity name, entity parent_id for breadcrumbs paths",
)
async def get_entity_info(
    entity_id: int,  # noqa: U100
    permission_module: PermissionsModules,  # noqa: U100
    entity_type: BreadcrumbsEntityTypes,
    entity: Union[Company, Site, Device, Task] = Depends(get_authorized_breadcrumbs_entity),
):
    response = {
        "id": entity.id,
        "name": entity.name,
        "parent_id": entity.parent_id,
        "parent_entity_type": entity.parent_entity_type,
    }
    if entity_type == BreadcrumbsEntityTypes.task:
        response["name"] = entity.external_id
    return response
