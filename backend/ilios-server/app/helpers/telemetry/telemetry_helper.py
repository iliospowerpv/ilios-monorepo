import base64
import logging
from typing import Union

from fastapi import HTTPException, status

from app.crud.errors import UniqueConstraintViolationError
from app.crud.telemetry_mapping import TelemetryDeviceMappingCRUD, TelemetrySiteMappingCRUD
from app.firestore_models.firestore_company_config import FSDevice, FSSite
from app.helpers.telemetry.firestore_client import FirestoreClient
from app.models.device import Device
from app.models.session import Session
from app.models.site import Site
from app.models.telemetry import DASProvidersEnum
from app.schema.telemetry import ConnectionCreateSchema, ConnectionUpdateSchema
from app.static import TelemetryMessages

logger = logging.getLogger(__name__)


def create_device_mapping_for_telemetry(site: Site, telemetry_mapping: dict, db_session: Session):
    telemetry_mapping_crud = TelemetryDeviceMappingCRUD(db_session)
    try:
        device_mapping = telemetry_mapping_crud.create_item(telemetry_mapping)
        logger.info(f"Created telemetry device mapping with id {device_mapping.id}")
    except UniqueConstraintViolationError:
        logger.exception(TelemetryMessages.device_mapping_already_exists)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.device_mapping_already_exists)
    # Update Firestore config
    try:
        firestore_client = FirestoreClient()
        fs_company_config = firestore_client.get_company_config(site.company_id)
        fs_site = fs_company_config.get_site_by_id(site.id)
        fs_site.devices.append(FSDevice(_id=device_mapping.device_id, external_id=device_mapping.telemetry_device_id))
        firestore_client.update_company_config(fs_company_config)
    except Exception as exception:
        telemetry_mapping_crud.delete_by_id(device_mapping.id)
        raise exception


def create_site_mapping_for_telemetry(site: Site, telemetry_mapping: dict, db_session: Session):
    telemetry_mapping_crud = TelemetrySiteMappingCRUD(db_session)
    try:
        site_mapping = telemetry_mapping_crud.create_item(telemetry_mapping)
        logger.info(f"Created telemetry site mapping with id {site_mapping.id}")
    except UniqueConstraintViolationError:
        logger.exception(TelemetryMessages.site_mapping_already_exists)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.site_mapping_already_exists)
    # Update Firestore config
    try:
        firestore_client = FirestoreClient()
        fs_company_config = firestore_client.get_company_config(site.company_id)
        fs_company_config.sites.append(
            FSSite(_id=site.id, connection_id=site_mapping.connection_id, external_id=site_mapping.telemetry_site_id)
        )
        firestore_client.update_company_config(fs_company_config)
    except Exception as exception:
        telemetry_mapping_crud.delete_by_id(site_mapping.id)
        raise exception


def delete_device_telemetry_config(device: Device):
    """Delete firestore config for the specific device"""
    try:
        firestore_client = FirestoreClient()
        fs_company_config = firestore_client.get_company_config(device.site.company_id)
        fs_site = fs_company_config.get_site_by_id(device.site_id)
        # remove device from the sites devices list
        fs_site.devices = [fs_device for fs_device in fs_site.devices if fs_device.id != device.id]
        firestore_client.update_company_config(fs_company_config)
    except Exception as exception:
        logger.exception(message := f"Telemetry API call failed: {str(exception)}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)


def format_das_credentials(
    provider: DASProvidersEnum, das_connection: Union[ConnectionCreateSchema, ConnectionUpdateSchema]
):
    """Depending on the provider, shape the token correctly:
    - KMC - return the <token> field as is
    - Also Energy - encode with base 64 pair of username and password separated with colon (:)"""

    credentials = None
    if provider == DASProvidersEnum.kmc and das_connection.token:
        credentials = das_connection.token
    elif provider == DASProvidersEnum.also_energy and das_connection.username and das_connection.password:
        # encode token string as bytes
        token_bytes = f"{das_connection.username}:{das_connection.password}".encode("utf-8")
        # encode with base64
        credentials_bytes = base64.b64encode(token_bytes)
        # decode bytes into string
        credentials = credentials_bytes.decode("utf-8")
    return credentials
