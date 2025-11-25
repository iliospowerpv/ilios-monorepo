"""Telemetry related endpoint serves O&M connections to telemetry providers"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.crud.das_connection import DASConnectionCRUD
from app.db.session import get_session
from app.firestore_models.firestore_company_config import FSCompanyConfig, FSConnection
from app.helpers.authorization import AuthorizedUser, SettingsPermissions
from app.helpers.authorization.project_access import get_authorized_company, get_authorized_connection
from app.helpers.telemetry.firestore_client import FirestoreClient
from app.helpers.telemetry.secrets_manager import GCPSecretsManager
from app.helpers.telemetry.telemetry_cloud_function_client import TelemetryFuncHTTPClient
from app.helpers.telemetry.telemetry_helper import format_das_credentials
from app.models.company import Company
from app.models.session import Session
from app.models.telemetry import DASConnection
from app.schema.telemetry import (
    ConnectionCreateSchema,
    ConnectionCreateSuccess,
    ConnectionDeleteSuccess,
    ConnectionsListSchema,
    ConnectionUpdateSchema,
    ConnectionUpdateSuccess,
    TelemetrySitesDevicesList,
)
from app.settings import settings
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions, TelemetryMessages

logger = logging.getLogger(__name__)
settings_connections_router = APIRouter()


@settings_connections_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ConnectionCreateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[
        Depends(get_authorized_company),
        Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit))),
    ],
)
async def create_das_connection(
    company_id: int,
    das_connection: ConnectionCreateSchema,
    db_session: Session = Depends(get_session),
):
    das_connection_crud = DASConnectionCRUD(db_session)
    # Validate connection name is unique within company
    if das_connection_crud.get_company_connection_by_name(company_id, das_connection.name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.connection_name_already_exists)

    credentials = format_das_credentials(das_connection.provider, das_connection)

    # Validate credentials
    TelemetryFuncHTTPClient().validate_token(das_connection.provider.name, credentials)

    das_connection_record = {
        "company_id": company_id,
        "name": das_connection.name,
        "provider": das_connection.provider,
        "secret_token_name": "",
    }
    connection = das_connection_crud.create_item(das_connection_record)
    # Prepare auth secret name in format `{env_name}-company-{company_id}-connection-{connection_id}
    secret_name = f"{settings.environment_name}-company-{company_id}-connection-{connection.id}"
    connection.secret_token_name = secret_name

    try:
        # Create secret in GCP
        secret_manager = GCPSecretsManager()
        secret_manager.create_secret(secret_name)
        secret_manager.add_secret_version(secret_name, credentials)

        # Create pipeline config in Firestore if not exists, otherwise update with new connection
        fs_connection = FSConnection(
            _id=connection.id,
            data_provider=das_connection.provider.name,
            token_secret_id=secret_manager.get_secret_version_id(secret_name),
        )
        firestore_client = FirestoreClient()
        fs_company_config = firestore_client.get_company_config(company_id)
        if fs_company_config is None:
            fs_company_config = FSCompanyConfig(_id=company_id, connections=[fs_connection])
            firestore_client.create_company_config(fs_company_config)
        else:
            fs_company_config.connections.append(fs_connection)
            firestore_client.update_company_config(fs_company_config)

        db_session.commit()
    except Exception as exception:
        das_connection_crud.delete_by_id(connection.id)
        raise exception

    return {"code": status.HTTP_201_CREATED, "message": TelemetryMessages.connection_create_success}


@settings_connections_router.get(
    "/",
    response_model=ConnectionsListSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
)
async def get_company_connections(
    company: Company = Depends(get_authorized_company),
):
    return {"items": company.das_connections}


@settings_connections_router.put(
    "/{connection_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ConnectionUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def update_das_connection(
    payload: ConnectionUpdateSchema,
    connection: DASConnection = Depends(get_authorized_connection),
    db_session: Session = Depends(get_session),
):
    das_connection_crud = DASConnectionCRUD(db_session)

    # Validate connection name is unique within company if name was updated
    if connection.name != payload.name:
        if das_connection_crud.get_company_connection_by_name(connection.company_id, payload.name):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.connection_name_already_exists)
        # Update connection name in DB
        das_connection_crud.update_by_id(connection.id, {"name": payload.name})

    # Update secret credentials has been changed
    credentials = format_das_credentials(connection.provider, payload)
    if credentials is not None:
        # Validate token
        TelemetryFuncHTTPClient().validate_token(connection.provider.name, credentials)

        secret_manager = GCPSecretsManager()
        secret_manager.add_secret_version(connection.secret_token_name, credentials)

    return {"code": status.HTTP_202_ACCEPTED, "message": TelemetryMessages.connection_update_success}


@settings_connections_router.delete(
    "/{connection_id}",
    response_model=ConnectionDeleteSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Hard delete DAS connection, connection configs from firebase and GCP secrets",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def delete_das_connection(
    connection: DASConnection = Depends(get_authorized_connection),
    db_session: Session = Depends(get_session),
):
    firestore_client = FirestoreClient()
    fs_company_config = firestore_client.get_company_config(connection.company_id)
    fs_company_config.delete_connection(connection.id)
    # If no other connections remove config from Firestore, otherwise update with new connections list
    if not fs_company_config.connections:
        firestore_client.delete_company_config(fs_company_config.id)
    else:
        firestore_client.update_company_config(fs_company_config)

    secret_manager = GCPSecretsManager()
    secret_manager.delete_secret(connection.secret_token_name)
    DASConnectionCRUD(db_session).delete_by_id(connection.id)
    return {"code": status.HTTP_200_OK, "message": TelemetryMessages.connection_delete_success}


@settings_connections_router.get(
    "/{connection_id}/sites",
    response_model=TelemetrySitesDevicesList,
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
    description="Fetch Telemetry sites related to DAS connection",
)
async def get_connection_sites(
    connection: DASConnection = Depends(get_authorized_connection),
):
    telemetry_sites = TelemetryFuncHTTPClient().get_telemetry_sites(
        connection.provider.name, GCPSecretsManager().get_secret_version_id(connection.secret_token_name)
    )
    return {"items": telemetry_sites}
