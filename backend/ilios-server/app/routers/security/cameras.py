"""Security related endpoint serves cameras module"""

import logging

from fastapi import APIRouter, Depends

from app.helpers.authorization import AuthorizedUser, SettingsPermissions
from app.helpers.security.rombus_client import RombusClient
from app.schema.camera import PotentialCamerasList
from app.static import PermissionsActions

logger = logging.getLogger(__name__)
cameras_router = APIRouter()


@cameras_router.get(
    "/",
    response_model=PotentialCamerasList,
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
)
async def get_site_potential_cameras_list():
    return {"items": RombusClient().get_cameras_list()}
