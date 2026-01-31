"""Telemetry related endpoint serves O&M connections to telemetry providers"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.crud.audit_log import AuditLogCRUD
from app.crud.das_connection import DASConnectionCRUD
from app.db.session import get_session
from app.firestore_models.firestore_company_config import FSCompanyConfig, FSConnection
from app.helpers.authorization import AuthorizedUser, SettingsPermissions
from app.helpers.authorization.project_access import get_authorized_company, get_authorized_connection
from app.helpers.portfolio_hub import resolve_company_hub_id
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


def _create_audit_log(request: Request, db_session: Session, action: str, details: str, is_success: bool = True):
    """Create an audit log entry for connection operations"""
    try:
        user_id = getattr(request.state, "current_user_id", None)
        AuditLogCRUD(db_session).create_item({
            "source": "telemetry_connections",
            "action": action,
            "details": details,
            "is_success": is_success,
            "user_id": user_id,
        })
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")


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
    request: Request,
    company_id: int,
    das_connection: ConnectionCreateSchema,
    db_session: Session = Depends(get_session),
):
    das_connection_crud = DASConnectionCRUD(db_session)
    if das_connection_crud.get_company_connection_by_name(company_id, das_connection.name):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.connection_name_already_exists)

    credentials = format_das_credentials(das_connection.provider, das_connection)
    
    test_status = "SUCCESS"
    test_message = None
    try:
        TelemetryFuncHTTPClient().validate_token(das_connection.provider.name, credentials)
    except HTTPException as e:
        test_status = "FAILURE"
        test_message = str(e.detail) if hasattr(e, "detail") else "Connection validation failed"
        raise
    except Exception as e:
        test_status = "FAILURE"
        test_message = str(e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Connection validation failed: {test_message}")

    owner_type = "company"
    owner_company_id = None
    
    if das_connection.share_with_portfolio:
        hub_id = resolve_company_hub_id(db_session, company_id)
        if hub_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Cannot share connection with portfolio: company is not part of a portfolio hub"
            )
        owner_type = "portfolio"
        owner_company_id = hub_id
    
    das_connection_record = {
        "company_id": company_id,
        "name": das_connection.name,
        "provider": das_connection.provider,
        "secret_token_name": "",
        "owner_type": owner_type,
        "owner_company_id": owner_company_id,
        "last_test_at": datetime.utcnow(),
        "last_test_status": test_status,
        "last_test_message": test_message,
    }
    connection = das_connection_crud.create_item(das_connection_record)
    secret_name = f"{settings.environment_name}-company-{company_id}-connection-{connection.id}"
    connection.secret_token_name = secret_name

    try:
        secret_manager = GCPSecretsManager()
        secret_manager.create_secret(secret_name)
        secret_manager.add_secret_version(secret_name, credentials)

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
        
        _create_audit_log(
            request,
            db_session,
            "connection_created",
            f"Created {owner_type} connection '{das_connection.name}' (ID: {connection.id}) for company {company_id}",
        )
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
    request: Request,
    payload: ConnectionUpdateSchema,
    connection: DASConnection = Depends(get_authorized_connection),
    db_session: Session = Depends(get_session),
):
    das_connection_crud = DASConnectionCRUD(db_session)

    if connection.name != payload.name:
        if das_connection_crud.get_company_connection_by_name(connection.company_id, payload.name):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, TelemetryMessages.connection_name_already_exists)
        das_connection_crud.update_by_id(connection.id, {"name": payload.name})

    credentials = format_das_credentials(connection.provider, payload)
    if credentials is not None:
        try:
            TelemetryFuncHTTPClient().validate_token(connection.provider.name, credentials)
            das_connection_crud.update_test_status(connection.id, "SUCCESS")
        except HTTPException as e:
            das_connection_crud.update_test_status(
                connection.id,
                "FAILURE",
                str(e.detail) if hasattr(e, "detail") else "Validation failed"
            )
            raise
        except Exception as e:
            das_connection_crud.update_test_status(connection.id, "FAILURE", str(e))
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Connection validation failed: {e}")

        secret_manager = GCPSecretsManager()
        secret_manager.add_secret_version(connection.secret_token_name, credentials)

    _create_audit_log(
        request,
        db_session,
        "connection_updated",
        f"Updated connection '{connection.name}' (ID: {connection.id})",
    )

    return {"code": status.HTTP_202_ACCEPTED, "message": TelemetryMessages.connection_update_success}


@settings_connections_router.delete(
    "/{connection_id}",
    response_model=ConnectionDeleteSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Hard delete DAS connection, connection configs from firebase and GCP secrets",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def delete_das_connection(
    request: Request,
    connection: DASConnection = Depends(get_authorized_connection),
    db_session: Session = Depends(get_session),
):
    connection_name = connection.name
    connection_id = connection.id
    company_id = connection.company_id
    
    firestore_client = FirestoreClient()
    fs_company_config = firestore_client.get_company_config(connection.company_id)
    if fs_company_config:
        fs_company_config.delete_connection(connection.id)
        if not fs_company_config.connections:
            firestore_client.delete_company_config(fs_company_config.id)
        else:
            firestore_client.update_company_config(fs_company_config)

    secret_manager = GCPSecretsManager()
    secret_manager.delete_secret(connection.secret_token_name)
    DASConnectionCRUD(db_session).delete_by_id(connection.id)
    
    _create_audit_log(
        request,
        db_session,
        "connection_deleted",
        f"Deleted connection '{connection_name}' (ID: {connection_id}) from company {company_id}",
    )
    
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
