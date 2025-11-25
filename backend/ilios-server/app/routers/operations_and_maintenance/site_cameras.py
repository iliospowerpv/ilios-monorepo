"""Cameras related endpoint serves O&M (Operations and Maintenance) security cameras module"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.helpers.authorization import AuthorizedUser, OnMPermissions
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.security.camera_helper import map_cameras_alerts
from app.helpers.security.rombus_client import RombusClient
from app.models.site import Site
from app.schema.camera import AlertSharedClipURL, CameraLiveStreamURL, CamerasAlertsList, SiteCamerasList
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions

logger = logging.getLogger(__name__)
om_site_cameras_router = APIRouter()


@om_site_cameras_router.get(
    "",
    response_model=SiteCamerasList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Retrieve cameras list with locations for site.",
    dependencies=[Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
)
async def get_site_cameras(
    site: Site = Depends(get_authorized_site),
):
    if not site.cameras_uuids:
        return {"items": []}
    rombus_client = RombusClient()
    rombus_cameras = rombus_client.get_cameras_list()
    cameras_locations = rombus_client.get_locations()
    # Map location uuid to location name
    cameras_locations = {location["uuid"]: location["name"] for location in cameras_locations}
    site_cameras = []
    for camera in rombus_cameras:
        if camera["uuid"] not in site.cameras_uuids:
            continue
        # Map rombus camera connection status and location
        camera["status"] = camera["connectionStatus"]
        camera["location"] = cameras_locations.get(camera["locationUuid"], "")
        site_cameras.append(camera)
    return {"items": site_cameras}


@om_site_cameras_router.get(
    "/{camera_uuid}/livestream",
    response_model=CameraLiveStreamURL,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Retrieve cameras list with locations for site.",
    dependencies=[Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
)
async def get_site_camera_livestream_url(
    camera_uuid: str,
    site: Site = Depends(get_authorized_site),
):
    if camera_uuid not in site.cameras_uuids:
        logger.warning(f"Camera UUID: {camera_uuid} is not attached to site ID: {site.id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    camera_livestream = RombusClient().get_or_create_shared_livestream(camera_uuid)
    return {"live_stream_url": camera_livestream["sharedLiveVideoStreamUrl"]}


@om_site_cameras_router.get(
    "/alerts",
    response_model=CamerasAlertsList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Retrieve cameras list with locations for site.",
    dependencies=[Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
)
async def get_site_cameras_alerts(
    site: Site = Depends(get_authorized_site),
):
    if not site.cameras_uuids:
        return {"items": []}
    rombus_client = RombusClient()
    rombus_cameras = rombus_client.get_cameras_list()
    site_cameras = [camera for camera in rombus_cameras if camera["uuid"] in site.cameras_uuids]
    alerts = rombus_client.get_policy_alerts(site.cameras_uuids)
    cameras_alerts = map_cameras_alerts(site_cameras, alerts)
    return {"items": cameras_alerts}


@om_site_cameras_router.get(
    "/alerts/{alert_uuid}/shared-clip",
    response_model=AlertSharedClipURL,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(get_authorized_site), Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
    description="Retrieve shared clip url for camera alert.",
)
async def get_alert_shared_clip_url(
    alert_uuid: str,
):
    return {"shared_clip_url": RombusClient().get_or_create_shared_alert_clip_url(alert_uuid)}
