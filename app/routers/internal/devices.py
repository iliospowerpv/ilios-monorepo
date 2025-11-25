import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.device import DeviceCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.helpers.telemetry.telemetry_helper import delete_device_telemetry_config
from app.models.device import DeviceStatuses
from app.static import DeviceMessages
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_devices_router = APIRouter()
internal_telemetry_devices_router = APIRouter()


@internal_telemetry_devices_router.patch(
    "/devices/{device_id}/deprecate",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_202_ACCEPTED,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Set device status as 'Deleted on DAS' and remove device from the telemetry config",
)
async def mark_device_as_deleted(
    device_id: int,
    db_session: Session = Depends(get_session),
):
    device_crud = DeviceCRUD(db_session)
    device = device_crud.get_by_id(device_id)
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=DeviceMessages.device_not_found)
    device_crud.update_by_id(device_id, {"status": DeviceStatuses.deleted_on_das})
    delete_device_telemetry_config(device)
    return {"code": status.HTTP_202_ACCEPTED, "message": DeviceMessages.device_deleted_on_das_success}
