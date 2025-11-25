import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authorization import AssetPermissions, AuthorizedUser, SettingsPermissions
from app.helpers.authorization.project_access import get_authorized_site_with_company_admin
from app.helpers.telemetry.secrets_manager import GCPSecretsManager
from app.helpers.telemetry.telemetry_cloud_function_client import TelemetryFuncHTTPClient
from app.helpers.telemetry.telemetry_helper import create_site_mapping_for_telemetry
from app.models.site import Site
from app.schema.telemetry import SiteMappingCreateSuccess, TelemetrySiteMappingSchema, TelemetrySitesDevicesList
from app.static import PermissionsActions, TelemetryMessages

logger = logging.getLogger(__name__)
telemetry_router = APIRouter()


@telemetry_router.post(
    "/sites/{site_id}/mapping",
    status_code=status.HTTP_201_CREATED,
    response_model=SiteMappingCreateSuccess,
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def create_site_mapping(
    mapping: TelemetrySiteMappingSchema,
    site: Site = Depends(get_authorized_site_with_company_admin),
    db_session: Session = Depends(get_session),
) -> dict:
    telemetry_mapping = mapping.model_dump()
    telemetry_mapping["site_id"] = site.id
    if mapping.connection_id not in [connection.id for connection in site.company.das_connections]:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    create_site_mapping_for_telemetry(site, telemetry_mapping, db_session)
    return {"code": status.HTTP_201_CREATED, "message": TelemetryMessages.site_mapping_create_success}


@telemetry_router.get(
    "/sites/{site_id}/devices",
    response_model=TelemetrySitesDevicesList,
    description="Fetch Telemetry devices related to telemetry site",
    # devices mapping is a part of Asset Management board, thus use Asset permission to control it
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_telemetry_site_devices(
    site: Site = Depends(get_authorized_site_with_company_admin),
):
    if site.das_connection:
        telemetry_devices = TelemetryFuncHTTPClient().get_telemetry_devices(
            site.das_connection.provider.name,
            GCPSecretsManager().get_secret_version_id(site.das_connection.secret_token_name),
            site.telemetry_mapping.telemetry_site_id,
        )
    else:
        logger.info(f"Can not fetch telemetry devices for site ID: {site.id}. No active DAS connection.")
        telemetry_devices = []
    return {"items": telemetry_devices}
