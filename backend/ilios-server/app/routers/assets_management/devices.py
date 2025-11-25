import logging
from copy import deepcopy

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.device import DeviceCRUD
from app.crud.device_document import DeviceDocumentCRUD
from app.db.object_utils import as_dict
from app.db.session import get_session
from app.filters.device_filters import SearchDeviceByName
from app.helpers.authentication import api_key_check
from app.helpers.authorization import AssetPermissions, AuthorizedUser
from app.helpers.authorization.project_access import get_authorized_device, get_authorized_site
from app.helpers.bq_data_sync_helper import DeviceCharacteristicsHandler
from app.helpers.device_helper import (
    get_availability_metrics,
    set_device_default_fields,
    validate_device_type_manufacturer,
)
from app.helpers.query_params_validator import validate_query_params
from app.helpers.telemetry.secrets_manager import GCPSecretsManager
from app.helpers.telemetry.telemetry_cloud_function_client import TelemetryFuncHTTPClient
from app.helpers.telemetry.telemetry_helper import create_device_mapping_for_telemetry
from app.models.device import Device, DeviceCategories, DeviceOrderByFieldEnum, DeviceStatuses
from app.models.device_document import DocumentCategories
from app.models.site import Site
from app.schema.device import (
    CreateDeviceSchema,
    DeviceCreationResponse,
    DeviceDetailsSchema,
    DeviceTechnicalDetailsUpdateSchema,
    DeviceUpdateSuccess,
    SiteDevicesSchema,
    UpdateDeviceGeneralInfoSchema,
    UpdateServiceDetailDeviceSchema,
)
from app.schema.om_device import TelemetryStaticDeviceData
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, DeviceMessages, PermissionsActions

logger = logging.getLogger(__name__)
devices_router = APIRouter()


@devices_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=DeviceCreationResponse,
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def create(
    device: CreateDeviceSchema,
    db_session: Session = Depends(get_session),
    site: Site = Depends(get_authorized_site),
) -> dict:
    device_payload = device.model_dump()
    telemetry_mapping = {
        "telemetry_device_id": device_payload.pop("telemetry_device_id"),
        "telemetry_device_name": device_payload.pop("telemetry_device_name"),
    }
    device_payload["site_id"] = site.id
    # update payload with default device fields
    set_device_default_fields(device_payload)
    # there is no sense to handle the IntegrityError since site existence is checked via get_authorized_site
    device = DeviceCRUD(db_session).create_item(device_payload)
    logger.info(f"Created device with id {device.id}")

    # Create Telemetry device mapping if telemetry fields provided
    if telemetry_mapping["telemetry_device_id"] and telemetry_mapping["telemetry_device_name"] and site.das_connection:
        telemetry_mapping["device_id"] = device.id
        create_device_mapping_for_telemetry(site, telemetry_mapping, db_session)
    return {"device_id": device.id, "code": 201, "message": "Device has been successfully created"}


@devices_router.get(
    "/",
    response_model=SiteDevicesSchema,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_site_devices(
    query_params: tuple = Depends(validate_query_params(order_by=DeviceOrderByFieldEnum)),
    *,
    site: Site = Depends(get_authorized_site),
    device_filter: SearchDeviceByName = FilterDepends(SearchDeviceByName),
    db_session: Session = Depends(get_session),
):
    skip, limit, order_by, order_direction = query_params
    total, devices = DeviceCRUD(db_session).get_site_devices(
        site.id, device_filter, skip, limit, order_by, order_direction
    )

    return {"items": devices, "skip": skip, "limit": limit, "total": total}


@devices_router.get(
    "/{device_id}",
    response_model=DeviceDetailsSchema,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_by_id(device: Device = Depends(get_authorized_device), db_session: Session = Depends(get_session)):
    documents_list = []
    document_crud = DeviceDocumentCRUD(db_session)
    device_documents = document_crud.get_device_documents(device.id)
    for category in DocumentCategories:
        documents_list.append(
            {"category": category, "items": [document for document in device_documents if document.category == category]}
        )

    # update service details with telemetry related data
    availability_metrics = get_availability_metrics(device)
    service_details = as_dict(device)
    service_details.update(availability_metrics)

    return {
        "general_info": device,
        "documents": documents_list,
        "service_detail": service_details,
        "technical_details": device.technical_details,
        "telemetry_mapping": device.telemetry_mapping,
    }


@devices_router.delete(
    "/{device_id}/internal",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def delete(device_id: int, db_session: Session = Depends(get_session)):
    deleted_count = DeviceCRUD(db_session).delete_by_id(device_id)
    if deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND)


@devices_router.put(
    "/{device_id}/general-info",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DeviceUpdateSuccess,
    summary="Update device 'General information' section",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def update_general_info(
    device_payload: UpdateDeviceGeneralInfoSchema,
    device: Device = Depends(get_authorized_device),
    db_session: Session = Depends(get_session),
):
    if device.status in [DeviceStatuses.decommissioned, DeviceStatuses.deleted_on_das]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=DeviceMessages.archived_device_update_error)
    device_payload = device_payload.model_dump()
    telemetry_mapping = {
        "telemetry_device_id": device_payload.pop("telemetry_device_id"),
        "telemetry_device_name": device_payload.pop("telemetry_device_name"),
    }
    validate_device_type_manufacturer(device.category, device_payload["type"], device_payload["manufacturer"])
    DeviceCRUD(db_session).update_by_id(device.id, device_payload)

    # Create Telemetry device mapping if telemetry fields provided
    if telemetry_mapping["telemetry_device_id"] and telemetry_mapping["telemetry_device_name"]:
        telemetry_mapping["device_id"] = device.id
        create_device_mapping_for_telemetry(device.site, telemetry_mapping, db_session)
    return {"code": status.HTTP_202_ACCEPTED, "message": DeviceMessages.device_update_success}


@devices_router.put(
    "/{device_id}/service-details",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DeviceUpdateSuccess,
    summary="Update device 'Service detail' section",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def update_service_detail(
    device_payload: UpdateServiceDetailDeviceSchema,
    device: Device = Depends(get_authorized_device),
    db_session: Session = Depends(get_session),
):
    DeviceCRUD(db_session).update_by_id(device.id, device_payload.model_dump())
    return {"code": status.HTTP_202_ACCEPTED, "message": DeviceMessages.device_update_success}


@devices_router.put(
    "/{device_id}/technical-details",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DeviceUpdateSuccess,
    summary="Update device 'Technical details' section",
    description="Be aware: each device category has specific data structure",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def update_technical_details(
    device_payload: DeviceTechnicalDetailsUpdateSchema,
    background_tasks: BackgroundTasks,
    device: Device = Depends(get_authorized_device),
    db_session: Session = Depends(get_session),
):
    # make a snapshot for difference comparison, cause changes after update will be reflected in the object
    technical_details_before_update = deepcopy(device.technical_details)

    # double-check device schema corresponds to the actual device category
    if device.category != device_payload.category:
        logger.warning(
            f"User tried to apply technical details of <{device_payload.category.value}> "
            f"to the <{device.category.value}> device"
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid technical details schema")

    device_payload = device_payload.model_dump(mode="json")
    # remove category field from the update payload
    device_payload.pop("category")
    DeviceCRUD(db_session).update_by_id(device.id, device_payload)

    # only after successful update, sync telemetry-valuable data with BQ for inverter and module
    if device.category in [DeviceCategories.inverter, DeviceCategories.module]:
        background_tasks.add_task(
            DeviceCharacteristicsHandler(device).sync_to_bq,
            old_record=technical_details_before_update,
            new_record=device_payload["technical_details"],
        )
    return {"code": status.HTTP_202_ACCEPTED, "message": DeviceMessages.device_update_success}


@devices_router.put(
    "/{device_id}/telemetry-details",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DeviceUpdateSuccess,
    description="Update device fields with information received from telemetry provider",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def update_device_with_telemetry_info(
    device: Device = Depends(get_authorized_device),
    db_session: Session = Depends(get_session),
):
    if any(
        [
            not device.site.das_connection,
            not device.telemetry_mapping,
            device.status in (DeviceStatuses.deleted_on_das, DeviceStatuses.decommissioned),
        ]
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=DeviceMessages.device_not_connected_to_das)

    telemetry_static_device_info = TelemetryFuncHTTPClient().get_device_static_info(
        device.site.das_connection.provider.name,
        GCPSecretsManager().get_secret_version_id(device.site.das_connection.secret_token_name),
        device.site.telemetry_mapping.telemetry_site_id,
        device.telemetry_mapping.telemetry_device_id,
    )
    if not telemetry_static_device_info:
        return {"code": status.HTTP_202_ACCEPTED, "message": DeviceMessages.no_telemetry_data_received}

    device_payload = TelemetryStaticDeviceData(
        category=telemetry_static_device_info["category"],
        asset_id=telemetry_static_device_info["id"],
        name=telemetry_static_device_info["name"],
        serial_number=telemetry_static_device_info["serial_number"],
        gateway_id=telemetry_static_device_info["gateway_id"],
        function_id=telemetry_static_device_info["function_id"],
        driver=telemetry_static_device_info["driver"],
        last_updated_date=telemetry_static_device_info["last_update_ts"],
    )

    DeviceCRUD(db_session).update_by_id(device.id, device_payload.model_dump(exclude_none=True))
    return {"code": status.HTTP_202_ACCEPTED, "message": DeviceMessages.device_telemetry_info_update_success}
