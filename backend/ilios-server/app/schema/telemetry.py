from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.models.telemetry import DASProvidersEnum
from app.schema.message import Success
from app.static import TelemetryMessages


class TelemetryHealthStatus(str, Enum):
    healthy = "HEALTHY"
    warn = "WARN"
    error = "ERROR"
    no_data = "NO_DATA"
    no_data_yet = "NO_DATA_YET"
    not_configured = "NOT_CONFIGURED"
    mapped_no_devices = "MAPPED_NO_DEVICES"


class ConnectionNameSchema(BaseModel):
    name: str = Field(examples=["Also Energy Connection 1"], min_length=2, max_length=100)


class ConnectionBaseSchema(ConnectionNameSchema):
    provider: DASProvidersEnum = Field(examples=["Also Energy"])


class ConnectionPayloadSchema(BaseModel):
    """Common schema for auth fields KMC and Also Energy"""

    # KMC fields
    token: Optional[str] = Field(None, examples=["kmc-s3cr3t_t0k3n"])
    # AE fields
    username: Optional[str] = Field(None, examples=["user19472"])
    password: Optional[str] = Field(None, examples=["112263kng"])


class ConnectionCreateSchema(ConnectionBaseSchema, ConnectionPayloadSchema):
    """Extend connection name+provider with payload"""
    
    share_with_portfolio: bool = Field(
        default=False,
        description="If True, connection will be shared with all companies in the portfolio hub"
    )

    @model_validator(mode="after")
    def verify_credentials_payload(self):
        """Depending on DAS Provider name, validate required credentials populated:
            - for KMC - token
            - for Also Energy - username and password.
        This required only for the creation case, for update empty credentials are allowed"""
        if self.provider == DASProvidersEnum.kmc:
            if not self.token:
                raise ValueError(f"The field <token> is required for the {DASProvidersEnum.kmc.value} provider")
        elif self.provider == DASProvidersEnum.also_energy:
            if not self.username or not self.password:
                raise ValueError(
                    f"The fields <username> and <password> are required for the {DASProvidersEnum.also_energy.value} "
                    f"provider"
                )
        return self


class ConnectionCreateSuccess(Success):
    message: str = Field(description="Success message", examples=[TelemetryMessages.connection_create_success])


class ConnectionSchema(ConnectionBaseSchema):
    id: int = Field(examples=[1])


class ConnectionsListSchema(BaseModel):
    items: list[ConnectionSchema]


class AvailableConnectionSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["AlsoEnergy Production"])
    provider: str = Field(examples=["Also Energy"])
    company_id: int = Field(examples=[1])
    company_name: str = Field(examples=["Acme Solar"])
    owner_type: str = Field(examples=["company"])
    owner_company_id: Optional[int] = Field(None, examples=[1])
    owner_company_name: Optional[str] = Field(None, examples=["Portfolio Hub Co"])
    last_test_at: Optional[datetime] = Field(None)
    last_test_status: Optional[str] = Field(None, examples=["SUCCESS"])
    last_test_message: Optional[str] = Field(None)


class AvailableConnectionsResponse(BaseModel):
    company_connections: list[AvailableConnectionSchema] = Field(
        default_factory=list,
        description="Connections owned by the company"
    )
    portfolio_connections: list[AvailableConnectionSchema] = Field(
        default_factory=list,
        description="Portfolio-shared connections from other companies in the same hub"
    )


class ConnectionUpdateSchema(ConnectionCreateSchema):
    """Exclude provider from the creation schema since it's not available for update"""

    provider: ClassVar[str] = None


class ConnectionUpdateSuccess(Success):
    message: str = Field(description="Success message", examples=[TelemetryMessages.connection_update_success])


class ConnectionDeleteSuccess(Success):
    message: str = Field(description="Success message", examples=[TelemetryMessages.connection_delete_success])


class TelemetrySiteDeviceSchema(BaseModel):
    """Common schema for telemetry site/device"""

    id: Union[str, int] = Field(examples=["21sad"])
    name: str = Field(examples=["Telemetry"])


class TelemetrySitesDevicesList(BaseModel):
    """Common schema for telemetry sites list/devices list"""

    items: Optional[list[TelemetrySiteDeviceSchema]]


class TelemetrySiteMappingSchema(BaseModel):
    connection_id: int = Field(examples=[2])
    telemetry_site_id: Union[str, int] = Field(examples=["ADSCXc1"])
    telemetry_site_name: str = Field(examples=["Telemetry Site 1"])


class SiteMappingCreateSuccess(Success):
    message: str = Field(description="Success message", examples=[TelemetryMessages.site_mapping_create_success])


class SiteMappingUpdateSuccess(Success):
    message: str = Field(description="Success message", examples=[TelemetryMessages.site_mapping_update_success])


class SiteMappingDeleteSuccess(Success):
    message: str = Field(description="Success message", examples=[TelemetryMessages.site_mapping_delete_success])


class ConnectionTestSchema(ConnectionPayloadSchema):
    provider: DASProvidersEnum = Field(examples=["Also Energy"])

    @model_validator(mode="after")
    def verify_credentials_payload(self):
        if self.provider == DASProvidersEnum.kmc:
            if not self.token:
                raise ValueError(f"The field <token> is required for the {DASProvidersEnum.kmc.value} provider")
        elif self.provider == DASProvidersEnum.also_energy:
            if not self.username or not self.password:
                raise ValueError(
                    f"The fields <username> and <password> are required for the {DASProvidersEnum.also_energy.value} provider"
                )
        return self


class ConnectionTestResponse(BaseModel):
    success: bool = Field(description="Whether connection test was successful")
    message: str = Field(description="Test result message")
    available_sites_count: Optional[int] = Field(None, description="Number of available DAS sites if test succeeded")
    provider: str = Field(description="DAS provider name")


class TelemetryHealthResponse(BaseModel):
    status: TelemetryHealthStatus = Field(description="Health status of telemetry data flow")
    last_data_at: Optional[datetime] = Field(None, description="Timestamp of last received data")
    data_delay_minutes: Optional[int] = Field(None, description="Minutes since last data received")
    last_error: Optional[str] = Field(None, description="Last error message if any")
    mapped_device_count: int = Field(0, description="Number of devices with telemetry mapping")
    expected_interval_minutes: int = Field(15, description="Expected data interval in minutes")
    is_connected: bool = Field(False, description="Whether site has a DAS connection")
    is_site_mapped: bool = Field(False, description="Whether site is mapped to a DAS site")


class TelemetryReadinessResponse(BaseModel):
    is_connected: bool = Field(False, description="Whether project has a DAS connection")
    is_site_mapped: bool = Field(False, description="Whether project is mapped to a DAS site")
    is_devices_mapped: bool = Field(False, description="Whether project has devices mapped")
    is_data_flowing: bool = Field(False, description="Whether telemetry data is flowing")
    connection_id: Optional[int] = Field(None, description="DAS connection ID if connected")
    connection_name: Optional[str] = Field(None, description="DAS connection name if connected")
    provider: Optional[str] = Field(None, description="DAS provider name if connected")
    telemetry_site_id: Optional[str] = Field(None, description="Mapped DAS site ID")
    telemetry_site_name: Optional[str] = Field(None, description="Mapped DAS site name")
    mapped_device_count: int = Field(0, description="Number of devices with telemetry mapping")
    total_eligible_device_count: int = Field(0, description="Total telemetry-eligible devices")
    credential_status: Optional[str] = Field(
        None,
        description=(
            "DAS connection credential status when connected "
            "(unverified/verified/invalid/expired); None when not connected"
        ),
    )


class DeviceMappingSchema(BaseModel):
    device_id: int = Field(description="Ilios device ID")
    telemetry_device_id: str = Field(description="External DAS device ID")
    telemetry_device_name: str = Field(description="External DAS device name")


class BulkDeviceMappingSchema(BaseModel):
    mappings: list[DeviceMappingSchema] = Field(description="List of device mappings")


class BulkDeviceMappingResponse(Success):
    message: str = Field(description="Success message", examples=[TelemetryMessages.bulk_device_mapping_success])
    successful_count: int = Field(description="Number of successful mappings")
    failed_count: int = Field(description="Number of failed mappings")
    errors: Optional[list[str]] = Field(None, description="List of error messages for failed mappings")


class DeviceMappingDeleteSuccess(Success):
    message: str = Field(description="Success message", examples=[TelemetryMessages.device_mapping_delete_success])


class CompanyProviderSchema(BaseModel):
    provider: str = Field(description="Provider enum key", examples=["kmc"])
    provider_display: str = Field(description="Provider display name", examples=["KMC"])
    connection_count: int = Field(default=0, description="Number of DAS connections currently using this provider")


class CompanyProvidersListSchema(BaseModel):
    items: list[CompanyProviderSchema] = Field(default_factory=list)


class AssignProviderSchema(BaseModel):
    provider: str = Field(description="Provider enum key to assign", examples=["kmc"])


class AssignProviderSuccess(Success):
    message: str = Field(default="Provider assigned successfully")


class RemoveProviderSuccess(Success):
    message: str = Field(default="Provider removed successfully")
