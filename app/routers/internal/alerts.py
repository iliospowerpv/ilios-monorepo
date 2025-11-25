import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.alert import AlertCRUD
from app.crud.device import DeviceCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.schema.alert import AlertCreateSchema, AlertCreationSuccess
from app.static import AlertMessages, DeviceMessages
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_alerts_router = APIRouter()


@internal_alerts_router.post(
    "/alerts",
    response_model=AlertCreationSuccess,
    status_code=status.HTTP_201_CREATED,
    responses={**HTTP_404_RESPONSE, **HTTP_403_RESPONSE},
    dependencies=[Depends(api_key_check)],
    description="API to create alerts by telemetry for devices that are connected with external telemetry devices.",
)
async def create_device_alert(
    alert: AlertCreateSchema,
    db_session: Session = Depends(get_session),
):
    if not DeviceCRUD(db_session).get_by_id(alert.device_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=DeviceMessages.device_not_found)
    alert_crud = AlertCRUD(db_session)
    if alert_crud.get_by_external_id(alert.device_id, alert.external_id):
        raise HTTPException(status.HTTP_409_CONFLICT, AlertMessages.alert_already_exists)
    alert_payload = alert.model_dump()
    alert_crud.create_item(alert_payload)
    return {"code": status.HTTP_201_CREATED, "message": AlertMessages.alert_create_success}
