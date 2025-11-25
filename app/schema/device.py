"""API Schema for device-related Endpoints"""

from datetime import date
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl, SerializeAsAny, field_validator

from app.models.device import (
    DeviceCategories,
    DeviceManufacturers,
    DeviceStatuses,
    DeviceTypes,
    DeviceWarrantyPeriodOptions,
)
from app.schema.common import SuccessUpdateSchema, date_field_validator
from app.schema.device_document import DocumentCategorySchema
from app.schema.device_technical_detail import (
    BatteryTechnicalDetailsSchema,
    CameraTechnicalDetailsSchema,
    CombinerBoxTechnicalDetailsSchema,
    InverterTechnicalDetailsViewSchema,
    MBODGatewayTechnicalDetailsSchema,
    MeterTechnicalDetailsSchema,
    ModemTechnicalDetailsSchema,
    ModuleTechnicalDetailsViewSchema,
    NetworkConnectionTechnicalDetailsSchema,
    NetworkGatewayTechnicalDetailsSchema,
    RachMountTechnicalDetailsSchema,
    TransformerTechnicalDetailsSchema,
    WeatherStationTechnicalDetailsSchema,
)
from app.schema.device_technical_detail.inverter import InverterTechnicalDetailsUpdateSchema
from app.schema.device_technical_detail.module import ModuleTechnicalDetailsUpdateSchema
from app.schema.paginator import BasePaginator
from app.static import DeviceMessages


def get_category_technical_details_schema(category, edit_mode=False):
    """Identify schema for the technical details based on the category.
    For the categories with required fields, maintain view and edit schemas separately"""
    category_schema_mapping = {
        DeviceCategories.inverter: InverterTechnicalDetailsViewSchema,
        DeviceCategories.module: ModuleTechnicalDetailsViewSchema,
        DeviceCategories.meter: MeterTechnicalDetailsSchema,
        DeviceCategories.rack_mount: RachMountTechnicalDetailsSchema,
        DeviceCategories.battery: BatteryTechnicalDetailsSchema,
        DeviceCategories.camera: CameraTechnicalDetailsSchema,
        DeviceCategories.combiner_box: CombinerBoxTechnicalDetailsSchema,
        DeviceCategories.modem: ModemTechnicalDetailsSchema,
        DeviceCategories.mbod_gateway: MBODGatewayTechnicalDetailsSchema,
        DeviceCategories.weather_station: WeatherStationTechnicalDetailsSchema,
        DeviceCategories.network_connection: NetworkConnectionTechnicalDetailsSchema,
        DeviceCategories.network_gateway: NetworkGatewayTechnicalDetailsSchema,
        DeviceCategories.transformer: TransformerTechnicalDetailsSchema,
    }
    # for the editing, ensure proper schemas for categories with required fields are used
    if edit_mode:
        schemas_with_required_fields = {
            DeviceCategories.module: ModuleTechnicalDetailsUpdateSchema,
            DeviceCategories.inverter: InverterTechnicalDetailsUpdateSchema,
        }
        category_schema_mapping.update(schemas_with_required_fields)
    category_technical_details_schema = category_schema_mapping.get(category)
    if not category_technical_details_schema:
        raise ValueError(f"No technical details schema defined for the category <{category.value}>")

    return category_technical_details_schema


def validate_device_status_user_input(status: DeviceStatuses):
    """Limit device status 'Deleted On Das' usage"""
    if status == DeviceStatuses.deleted_on_das:
        raise ValueError(f"Cannot set device status to <{DeviceStatuses.deleted_on_das.value}>, it's for internal usage")
    return status


class BaseDeviceSchema(BaseModel):
    """Includes only required fields, which need to be populated during device creation"""

    asset_id: Optional[str] = Field(None, examples=["1344ASD12"], min_length=2, max_length=100)
    status: DeviceStatuses
    name: str = Field(examples=["Basic Inverter"], min_length=2, max_length=100)
    category: DeviceCategories
    type: Optional[DeviceTypes] = Field(None, validate_default=True)
    manufacturer: Optional[DeviceManufacturers] = Field(None, validate_default=True)
    model: Optional[str] = Field(None, examples=["1AD212"], min_length=2, max_length=100)
    serial_number: Optional[str] = Field(None, examples=["1232CDSA"], min_length=2, max_length=100)
    # it should be read only, ensure to exclude it from the update schemas
    das_connection_status: str = Field(examples=["Connected"])

    @field_validator("asset_id")
    @classmethod
    def asset_id_upper_case(cls, asset_id):
        return asset_id.upper() if asset_id else None


class GeneralInfoDeviceSchema(BaseDeviceSchema):
    """Extends required fields of the general info section with non-required one"""

    warranty_effective_date: Optional[date] = Field(default=None, examples=["2028-01-21"])
    warranty_term: Optional[str] = Field(
        default=None, examples=["No, we don't cover if dog eats your solar battery"], max_length=100
    )
    gateway_id: Optional[str] = Field(default=None, examples=["000CC6817B99"], max_length=100)
    function_id: Optional[str] = Field(default=None, examples=["PV11"], max_length=100)
    driver: Optional[str] = Field(default=None, examples=["Greenland 1.12"], max_length=100)
    install_date: Optional[date] = Field(default=None, examples=["2019-12-20"])
    decommissioned_date: Optional[date] = Field(default=None, examples=["2023-09-13"])
    last_updated_date: Optional[date] = Field(default=None, examples=["2024-06-11"])


class ServiceDetailBaseDeviceSchema(BaseModel):
    # model fields
    lifetime: Optional[str] = Field(default=None, examples=["764 days (>2 years)"], max_length=100)
    warranty_period: Optional[DeviceWarrantyPeriodOptions] = None
    next_scheduled_service_date: Optional[date] = Field(default=None, examples=["2025-06-13"])


class UpdateServiceDetailDeviceSchema(ServiceDetailBaseDeviceSchema):
    # ensure input date is validated
    _validate_date = field_validator("next_scheduled_service_date", mode="before")(date_field_validator)


class ServiceDetailDeviceSchema(ServiceDetailBaseDeviceSchema):
    # hardcoded fields
    test_interval: Optional[str] = Field(default="TBD", examples=["60 days"])
    failure_rate: Optional[str] = Field(default="TBD", examples=["3.5 / 4"])
    mtbf: Optional[str | int] = Field(
        None, examples=["137 / 112"], serialization_alias="mtbr"
    )  # meantime between failures
    mttr: Optional[str | int] = Field(None, examples=["1 / 0.3"])  # meantime to recovery/restore
    availability: Optional[str] = Field(default="TBD", examples=["80% / 92%"])
    open_repair_tickets_count: Optional[str] = Field(default="TBD", examples=[12])


class CreateDeviceSchema(BaseModel):
    name: str = Field(examples=["Basic Inverter"], min_length=2, max_length=100)
    category: DeviceCategories
    telemetry_device_id: Optional[str] = Field(None, examples=["131ads"])
    telemetry_device_name: Optional[str] = Field(None, examples=["Telemetry Device 1"])


class UpdateDeviceGeneralInfoSchema(GeneralInfoDeviceSchema):
    category: ClassVar[DeviceCategories]  # exclude from device update
    das_connection_status: ClassVar

    telemetry_device_id: Optional[str] = Field(None, examples=["131ads"])
    telemetry_device_name: Optional[str] = Field(None, examples=["Telemetry Device 1"])

    _validate_device_status_input = field_validator("status")(validate_device_status_user_input)
    _validate_date = field_validator(
        "warranty_effective_date", "install_date", "decommissioned_date", "last_updated_date", mode="before"
    )(date_field_validator)


class DeviceTechnicalDetailsUpdateSchema(BaseModel):
    """Having both category and payload allows to validate technical details against category on the schema level"""

    category: DeviceCategories
    technical_details: Dict[str, Any] = Field(validate_default=True)

    @field_validator("technical_details")
    @classmethod
    def validate_technical_detail(cls, value, info):  # noqa: U100
        category = info.data.get("category")
        technical_details_schema = get_category_technical_details_schema(category, edit_mode=True)
        return technical_details_schema(**value).model_dump()


class DeviceListSchema(GeneralInfoDeviceSchema, ServiceDetailBaseDeviceSchema):
    id: int = Field(examples=[1])
    health: str = Field("green", examples=["green"])
    # keep fields below empty until Customer defines their value
    capacity: str = Field("", examples=[1])
    link_to_warranty_document: SerializeAsAny[HttpUrl] = Field("", examples=["https://example.com"])
    issue: str = Field("", examples=[""])
    maintenance: str = Field("", examples=[""])
    uptime_availability: str = Field("", examples=[""])


class SiteDevicesSchema(BasePaginator):
    items: Optional[List[DeviceListSchema]]


class DeviceCreationResponse(BaseModel):
    message: str = Field(description="Success message", examples=["Device has been successfully created"])
    code: int = Field(description="Success status code", examples=[201])
    device_id: int = Field(description="ID of newly created device", examples=[1])


class TelemetryDeviceMappingSchema(BaseModel):
    telemetry_device_id: Optional[str] = Field(None, examples=["131ads"])
    telemetry_device_name: Optional[str] = Field(None, examples=["Telemetry Device 1"])


class DeviceDetailsSchema(BaseModel):
    general_info: GeneralInfoDeviceSchema
    technical_details: Any = Field(validate_default=True, examples=[InverterTechnicalDetailsViewSchema().model_dump()])
    documents: list[DocumentCategorySchema]
    service_detail: ServiceDetailDeviceSchema
    telemetry_mapping: Optional[TelemetryDeviceMappingSchema] = Field(None)

    @field_validator("technical_details")
    @classmethod
    def validate_technical_details(cls, technical_details_value, info):
        """Based on the category, parse technical details into corresponding models"""
        # to parse schema properly, use empty dict instead of None
        if technical_details_value is None:
            technical_details_value = {}
        category = info.data.get("general_info").category
        technical_details_schema = get_category_technical_details_schema(category)
        return technical_details_schema(**technical_details_value).model_dump()


class DeviceUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=[DeviceMessages.device_update_success])
