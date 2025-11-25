from typing import ClassVar, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.models.telemetry import DASProvidersEnum
from app.schema.message import Success
from app.static import TelemetryMessages


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
