import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.crud.audit_log import AuditLogCRUD
from app.db.session import get_session
from app.helpers.authorization import AssetPermissions, AuthorizedUser, SettingsPermissions
from app.helpers.authorization.project_access import (
    get_authorized_company,
    get_authorized_device,
    get_authorized_site,
    get_authorized_site_with_company_admin,
)
from app.models.company import Company
from app.helpers.telemetry.bigquery.device import TelemetryDeviceBigQuery
from app.helpers.telemetry.secrets_manager import GCPSecretsManager
from app.helpers.telemetry.telemetry_cloud_function_client import TelemetryFuncHTTPClient
from app.helpers.telemetry.telemetry_helper import (
    create_device_mapping_for_telemetry,
    create_site_mapping_for_telemetry,
    delete_device_mapping_for_telemetry,
    delete_site_mapping_for_telemetry,
    format_das_credentials,
    update_site_mapping_for_telemetry,
)
from app.models.device import Device, DeviceCategories
from app.models.site import Site
from app.schema.telemetry import (
    AssignProviderSchema,
    AssignProviderSuccess,
    AvailableConnectionSchema,
    AvailableConnectionsResponse,
    BulkDeviceMappingResponse,
    BulkDeviceMappingSchema,
    CompanyProviderSchema,
    CompanyProvidersListSchema,
    ConnectionTestResponse,
    ConnectionTestSchema,
    DeviceMappingDeleteSuccess,
    RemoveProviderSuccess,
    SiteMappingCreateSuccess,
    SiteMappingDeleteSuccess,
    SiteMappingUpdateSuccess,
    TelemetryHealthResponse,
    TelemetryHealthStatus,
    TelemetryReadinessResponse,
    TelemetrySiteMappingSchema,
    TelemetrySitesDevicesList,
)
from app.static import PermissionsActions, TelemetryMessages

logger = logging.getLogger(__name__)
telemetry_router = APIRouter()

TELEMETRY_ELIGIBLE_CATEGORIES = [DeviceCategories.inverter, DeviceCategories.module, DeviceCategories.weather_station]


def _create_audit_log(request: Request, db_session: Session, action: str, details: str, is_success: bool = True):
    """Create an audit log entry for telemetry operations"""
    try:
        user_id = getattr(request.state, "current_user_id", None)
        AuditLogCRUD(db_session).create_item({
            "source": "telemetry",
            "action": action,
            "details": details,
            "is_success": is_success,
            "user_id": user_id,
        })
    except Exception as e:
        logger.warning(f"Failed to create audit log: {e}")


@telemetry_router.post(
    "/connections/test",
    response_model=ConnectionTestResponse,
    description="Test DAS connection credentials before saving",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def test_connection(
    test_payload: ConnectionTestSchema,
):
    """Test connection to DAS provider with provided credentials"""
    # Create a temporary object that format_das_credentials can accept
    class TempCredentials:
        def __init__(self, payload: ConnectionTestSchema):
            self.token = payload.token
            self.username = payload.username
            self.password = payload.password

    temp_creds = TempCredentials(test_payload)
    credentials = format_das_credentials(test_payload.provider, temp_creds)

    try:
        TelemetryFuncHTTPClient().validate_token(test_payload.provider.name, credentials)

        return ConnectionTestResponse(
            success=True,
            message=str(TelemetryMessages.connection_test_success),
            available_sites_count=None,
            provider=test_payload.provider.value,
        )

    except HTTPException as e:
        return ConnectionTestResponse(
            success=False,
            message=str(e.detail) if hasattr(e, "detail") else str(TelemetryMessages.connection_test_failed),
            available_sites_count=None,
            provider=test_payload.provider.value,
        )
    except Exception as e:
        logger.exception(f"Connection test failed: {e}")
        return ConnectionTestResponse(
            success=False,
            message=str(TelemetryMessages.connection_test_failed),
            available_sites_count=None,
            provider=test_payload.provider.value,
        )


@telemetry_router.get(
    "/connections/available",
    response_model=AvailableConnectionsResponse,
    description="Get DAS connections available for a company, grouped by ownership type",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_available_connections(
    company_id: int,
    db_session: Session = Depends(get_session),
):
    """Get all DAS connections available for a company.
    
    Returns connections grouped by:
    - company_connections: Connections owned by this company
    - portfolio_connections: Portfolio-shared connections from other companies in same hub
    """
    from app.crud.das_connection import DASConnectionCRUD
    from app.models.company import Company
    
    company = db_session.query(Company).get(company_id)
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    
    grouped = DASConnectionCRUD(db_session).get_available_connections_grouped(company_id)
    
    def _serialize_connection(conn):
        return AvailableConnectionSchema(
            id=conn.id,
            name=conn.name,
            provider=conn.provider.value,
            company_id=conn.company_id,
            company_name=conn.company.name if conn.company else "Unknown",
            owner_type=conn.owner_type,
            owner_company_id=conn.owner_company_id,
            owner_company_name=conn.owner_company.name if conn.owner_company else None,
            last_test_at=conn.last_test_at,
            last_test_status=conn.last_test_status,
            last_test_message=conn.last_test_message,
        )
    
    return AvailableConnectionsResponse(
        company_connections=[_serialize_connection(c) for c in grouped["company_connections"]],
        portfolio_connections=[_serialize_connection(c) for c in grouped["portfolio_connections"]],
    )


@telemetry_router.get(
    "/sites/{site_id}/available-connections",
    response_model=AvailableConnectionsResponse,
    description="Get DAS connections available for this site (company + hub shared)",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_site_available_connections(
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    """Get all DAS connections available for this site.
    
    Returns connections grouped by:
    - company_connections: Connections owned by the site's company
    - portfolio_connections: Portfolio-shared connections from other companies in same hub
    """
    from app.crud.das_connection import DASConnectionCRUD
    
    grouped = DASConnectionCRUD(db_session).get_available_connections_grouped(site.company_id)
    
    def _serialize_connection(conn):
        return AvailableConnectionSchema(
            id=conn.id,
            name=conn.name,
            provider=conn.provider.value,
            company_id=conn.company_id,
            company_name=conn.company.name if conn.company else "Unknown",
            owner_type=conn.owner_type,
            owner_company_id=conn.owner_company_id,
            owner_company_name=conn.owner_company.name if conn.owner_company else None,
            last_test_at=conn.last_test_at,
            last_test_status=conn.last_test_status,
            last_test_message=conn.last_test_message,
        )
    
    return AvailableConnectionsResponse(
        company_connections=[_serialize_connection(c) for c in grouped["company_connections"]],
        portfolio_connections=[_serialize_connection(c) for c in grouped["portfolio_connections"]],
    )


@telemetry_router.post(
    "/sites/{site_id}/mapping",
    status_code=status.HTTP_201_CREATED,
    response_model=SiteMappingCreateSuccess,
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def create_site_mapping(
    request: Request,
    mapping: TelemetrySiteMappingSchema,
    site: Site = Depends(get_authorized_site_with_company_admin),
    db_session: Session = Depends(get_session),
) -> dict:
    from app.crud.das_connection import DASConnectionCRUD
    
    telemetry_mapping = mapping.model_dump()
    telemetry_mapping["site_id"] = site.id
    
    accessible_connections = DASConnectionCRUD(db_session).get_hub_connections(site.company_id)
    accessible_connection_ids = [conn.id for conn in accessible_connections]
    
    if mapping.connection_id not in accessible_connection_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Connection not accessible to this company")
    create_site_mapping_for_telemetry(site, telemetry_mapping, db_session)

    _create_audit_log(
        request,
        db_session,
        "site_mapping_created",
        f"Site {site.id} mapped to DAS site {mapping.telemetry_site_id} ({mapping.telemetry_site_name})",
    )

    return {"code": status.HTTP_201_CREATED, "message": TelemetryMessages.site_mapping_create_success}


@telemetry_router.put(
    "/sites/{site_id}/mapping",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SiteMappingUpdateSuccess,
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def update_site_mapping(
    request: Request,
    mapping: TelemetrySiteMappingSchema,
    site: Site = Depends(get_authorized_site_with_company_admin),
    db_session: Session = Depends(get_session),
) -> dict:
    """Update existing site mapping"""
    from app.crud.das_connection import DASConnectionCRUD
    
    telemetry_mapping = mapping.model_dump()
    accessible_connections = DASConnectionCRUD(db_session).get_hub_connections(site.company_id)
    accessible_connection_ids = [conn.id for conn in accessible_connections]
    
    if mapping.connection_id not in accessible_connection_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Connection not accessible to this company")
    update_site_mapping_for_telemetry(site, telemetry_mapping, db_session)

    _create_audit_log(
        request,
        db_session,
        "site_mapping_updated",
        f"Site {site.id} mapping updated to DAS site {mapping.telemetry_site_id} ({mapping.telemetry_site_name})",
    )

    return {"code": status.HTTP_202_ACCEPTED, "message": TelemetryMessages.site_mapping_update_success}


@telemetry_router.delete(
    "/sites/{site_id}/mapping",
    response_model=SiteMappingDeleteSuccess,
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def delete_site_mapping(
    request: Request,
    site: Site = Depends(get_authorized_site_with_company_admin),
    db_session: Session = Depends(get_session),
) -> dict:
    """Delete site mapping and clean up Firestore config"""
    old_mapping_info = f"DAS site {site.telemetry_mapping.telemetry_site_id}" if site.telemetry_mapping else "unknown"
    delete_site_mapping_for_telemetry(site, db_session)

    _create_audit_log(
        request,
        db_session,
        "site_mapping_deleted",
        f"Site {site.id} mapping removed from {old_mapping_info}",
    )

    return {"code": status.HTTP_200_OK, "message": TelemetryMessages.site_mapping_delete_success}


@telemetry_router.get(
    "/sites/{site_id}/devices",
    response_model=TelemetrySitesDevicesList,
    description="Fetch Telemetry devices related to telemetry site",
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


@telemetry_router.get(
    "/sites/{site_id}/health",
    response_model=TelemetryHealthResponse,
    description="Get telemetry health status for a site",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_site_telemetry_health(
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    """Get telemetry health derived from BigQuery device_last_report_ts"""
    is_connected = site.das_connection is not None
    is_site_mapped = site.telemetry_mapping is not None

    if not is_connected or not is_site_mapped:
        return TelemetryHealthResponse(
            status=TelemetryHealthStatus.not_configured,
            last_data_at=None,
            data_delay_minutes=None,
            last_error=None,
            mapped_device_count=0,
            expected_interval_minutes=15,
            is_connected=is_connected,
            is_site_mapped=is_site_mapped,
        )

    # Get mapped devices
    mapped_devices = [
        device for device in site.devices
        if device.telemetry_mapping is not None and device.category in TELEMETRY_ELIGIBLE_CATEGORIES
    ]
    mapped_device_count = len(mapped_devices)

    if mapped_device_count == 0:
        return TelemetryHealthResponse(
            status=TelemetryHealthStatus.no_data,
            last_data_at=None,
            data_delay_minutes=None,
            last_error=None,
            mapped_device_count=0,
            expected_interval_minutes=15,
            is_connected=is_connected,
            is_site_mapped=is_site_mapped,
        )

    # Query BigQuery for last reported timestamps
    device_ids = [device.id for device in mapped_devices]
    try:
        bq_client = TelemetryDeviceBigQuery()
        site_tz = getattr(site, "timezone", None) or "UTC"
        last_reported_data = bq_client.get_device_last_reported(device_ids, site_tz)

        # Find the most recent data timestamp
        last_data_at = None
        if last_reported_data:
            for device_data in last_reported_data:
                if device_data and device_data.get("last_report_ts"):
                    ts = device_data["last_report_ts"]
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if last_data_at is None or ts > last_data_at:
                        last_data_at = ts

        # Calculate health status
        now = datetime.now(timezone.utc)
        data_delay_minutes = None
        if last_data_at:
            if last_data_at.tzinfo is None:
                last_data_at = last_data_at.replace(tzinfo=timezone.utc)
            data_delay = now - last_data_at
            data_delay_minutes = int(data_delay.total_seconds() / 60)

            # Status thresholds
            if data_delay_minutes <= 30:
                health_status = TelemetryHealthStatus.healthy
            elif data_delay_minutes <= 120:
                health_status = TelemetryHealthStatus.warn
            else:
                health_status = TelemetryHealthStatus.error
        else:
            health_status = TelemetryHealthStatus.no_data

        return TelemetryHealthResponse(
            status=health_status,
            last_data_at=last_data_at,
            data_delay_minutes=data_delay_minutes,
            last_error=None,
            mapped_device_count=mapped_device_count,
            expected_interval_minutes=15,
            is_connected=is_connected,
            is_site_mapped=is_site_mapped,
        )

    except Exception as e:
        logger.exception(f"Failed to fetch telemetry health: {e}")
        return TelemetryHealthResponse(
            status=TelemetryHealthStatus.error,
            last_data_at=None,
            data_delay_minutes=None,
            last_error=str(e),
            mapped_device_count=mapped_device_count,
            expected_interval_minutes=15,
            is_connected=is_connected,
            is_site_mapped=is_site_mapped,
        )


@telemetry_router.get(
    "/sites/{site_id}/readiness",
    response_model=TelemetryReadinessResponse,
    description="Get telemetry readiness status for a site",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_site_telemetry_readiness(
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    """Get telemetry readiness/configuration status for wizard UI"""
    is_connected = site.das_connection is not None
    is_site_mapped = site.telemetry_mapping is not None

    # Count telemetry-eligible devices
    eligible_devices = [d for d in site.devices if d.category in TELEMETRY_ELIGIBLE_CATEGORIES]
    total_eligible = len(eligible_devices)
    mapped_devices = [d for d in eligible_devices if d.telemetry_mapping is not None]
    mapped_count = len(mapped_devices)
    is_devices_mapped = mapped_count > 0

    # Determine if data is flowing (basic check - has mapped devices and recent health)
    is_data_flowing = False
    if is_connected and is_site_mapped and mapped_count > 0:
        try:
            device_ids = [d.id for d in mapped_devices]
            bq_client = TelemetryDeviceBigQuery()
            site_tz = getattr(site, "timezone", None) or "UTC"
            last_reported = bq_client.get_device_last_reported(device_ids, site_tz)
            if last_reported and any(d.get("last_report_ts") for d in last_reported if d):
                is_data_flowing = True
        except Exception as e:
            logger.warning(f"Failed to check data flow: {e}")

    return TelemetryReadinessResponse(
        is_connected=is_connected,
        is_site_mapped=is_site_mapped,
        is_devices_mapped=is_devices_mapped,
        is_data_flowing=is_data_flowing,
        connection_id=site.das_connection.id if site.das_connection else None,
        connection_name=site.das_connection.name if site.das_connection else None,
        provider=site.das_connection.provider.value if site.das_connection else None,
        telemetry_site_id=site.telemetry_mapping.telemetry_site_id if site.telemetry_mapping else None,
        telemetry_site_name=site.telemetry_mapping.telemetry_site_name if site.telemetry_mapping else None,
        mapped_device_count=mapped_count,
        total_eligible_device_count=total_eligible,
    )


@telemetry_router.post(
    "/sites/{site_id}/devices/bulk-mapping",
    response_model=BulkDeviceMappingResponse,
    description="Bulk map devices to telemetry devices",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def bulk_map_devices(
    request: Request,
    bulk_mapping: BulkDeviceMappingSchema,
    site: Site = Depends(get_authorized_site_with_company_admin),
    db_session: Session = Depends(get_session),
):
    """Bulk map existing devices to telemetry devices"""
    if not site.das_connection or not site.telemetry_mapping:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Site must have a DAS connection and site mapping before mapping devices",
        )

    successful = 0
    failed = 0
    errors = []

    # Get all device IDs for this site
    site_device_ids = {device.id for device in site.devices}

    for mapping in bulk_mapping.mappings:
        if mapping.device_id not in site_device_ids:
            errors.append(f"Device {mapping.device_id} does not belong to this site")
            failed += 1
            continue

        device = next((d for d in site.devices if d.id == mapping.device_id), None)
        if not device:
            errors.append(f"Device {mapping.device_id} not found")
            failed += 1
            continue

        if device.category not in TELEMETRY_ELIGIBLE_CATEGORIES:
            errors.append(f"Device {mapping.device_id} is not telemetry-eligible (category: {device.category})")
            failed += 1
            continue

        try:
            telemetry_mapping_data = {
                "device_id": mapping.device_id,
                "telemetry_device_id": mapping.telemetry_device_id,
                "telemetry_device_name": mapping.telemetry_device_name,
            }
            create_device_mapping_for_telemetry(site, telemetry_mapping_data, db_session)
            successful += 1
        except HTTPException as e:
            errors.append(f"Device {mapping.device_id}: {e.detail}")
            failed += 1
        except Exception as e:
            errors.append(f"Device {mapping.device_id}: {str(e)}")
            failed += 1

    _create_audit_log(
        request,
        db_session,
        "bulk_device_mapping",
        f"Bulk device mapping on site {site.id}: {successful} successful, {failed} failed",
        is_success=(failed == 0),
    )

    return BulkDeviceMappingResponse(
        code=status.HTTP_200_OK,
        message=str(TelemetryMessages.bulk_device_mapping_success),
        successful_count=successful,
        failed_count=failed,
        errors=errors if errors else None,
    )


@telemetry_router.delete(
    "/devices/{device_id}/mapping",
    response_model=DeviceMappingDeleteSuccess,
    description="Delete device telemetry mapping",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.edit)))],
)
async def delete_device_mapping(
    request: Request,
    device: Device = Depends(get_authorized_device),
    db_session: Session = Depends(get_session),
):
    """Delete device telemetry mapping"""
    old_mapping_info = (
        f"DAS device {device.telemetry_mapping.telemetry_device_id}" if device.telemetry_mapping else "unknown"
    )
    delete_device_mapping_for_telemetry(device, db_session)

    _create_audit_log(
        request,
        db_session,
        "device_mapping_deleted",
        f"Device {device.id} mapping removed from {old_mapping_info}",
    )

    return {"code": status.HTTP_200_OK, "message": TelemetryMessages.device_mapping_delete_success}


@telemetry_router.get(
    "/sites/{site_id}/eligible-devices",
    description="Get telemetry-eligible devices for a site with mapping status",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_eligible_devices(
    site: Site = Depends(get_authorized_site),
):
    """Get list of telemetry-eligible devices with their mapping status"""
    eligible_devices = []
    for device in site.devices:
        if device.category in TELEMETRY_ELIGIBLE_CATEGORIES:
            eligible_devices.append({
                "id": device.id,
                "name": device.name,
                "category": device.category.value if device.category else None,
                "serial_number": device.serial_number,
                "is_mapped": device.telemetry_mapping is not None,
                "telemetry_device_id": (
                    device.telemetry_mapping.telemetry_device_id if device.telemetry_mapping else None
                ),
                "telemetry_device_name": (
                    device.telemetry_mapping.telemetry_device_name if device.telemetry_mapping else None
                ),
            })
    return {"items": eligible_devices, "total": len(eligible_devices)}


@telemetry_router.get(
    "/companies/{company_id}/providers",
    response_model=CompanyProvidersListSchema,
    description="Get telemetry providers assigned to a company",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
)
async def get_company_providers(
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    from app.crud.company_das_provider import CompanyDASProviderCRUD

    providers = CompanyDASProviderCRUD(db_session).get_providers(company.id)
    return CompanyProvidersListSchema(
        items=[
            CompanyProviderSchema(
                provider=p.provider.name,
                provider_display=p.provider.value,
            )
            for p in providers
        ]
    )


@telemetry_router.post(
    "/companies/{company_id}/providers",
    response_model=AssignProviderSuccess,
    status_code=status.HTTP_201_CREATED,
    description="Assign a telemetry provider to a company",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def assign_company_provider(
    request: Request,
    payload: AssignProviderSchema,
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    from app.crud.company_das_provider import CompanyDASProviderCRUD
    from app.models.telemetry import DASProvidersEnum

    try:
        provider_enum = DASProvidersEnum[payload.provider]
    except KeyError:
        valid = [p.name for p in DASProvidersEnum]
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid provider '{payload.provider}'. Valid providers: {valid}",
        )

    CompanyDASProviderCRUD(db_session).assign_provider(company.id, provider_enum)

    _create_audit_log(
        request,
        db_session,
        "company_provider_assigned",
        f"Provider '{provider_enum.value}' assigned to company {company.id}",
    )

    return AssignProviderSuccess(code=status.HTTP_201_CREATED, message="Provider assigned successfully")


@telemetry_router.delete(
    "/companies/{company_id}/providers/{provider}",
    response_model=RemoveProviderSuccess,
    description="Remove a telemetry provider from a company",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def remove_company_provider(
    request: Request,
    provider: str,
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    from app.crud.company_das_provider import CompanyDASProviderCRUD
    from app.models.telemetry import DASProvidersEnum

    try:
        provider_enum = DASProvidersEnum[provider]
    except KeyError:
        valid = [p.name for p in DASProvidersEnum]
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid provider '{provider}'. Valid providers: {valid}",
        )

    deleted = CompanyDASProviderCRUD(db_session).remove_provider(company.id, provider_enum)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider not assigned to this company")

    _create_audit_log(
        request,
        db_session,
        "company_provider_removed",
        f"Provider '{provider_enum.value}' removed from company {company.id}",
    )

    return RemoveProviderSuccess(code=status.HTTP_200_OK, message="Provider removed successfully")
