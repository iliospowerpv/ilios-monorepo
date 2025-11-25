"""API Schema for O&M device-related Endpoints"""

import logging
from datetime import datetime
from typing import ClassVar, List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.models.device import DeviceCategories, DeviceStatuses, DeviceTypes
from app.schema.alert import AlertOverviewSchema
from app.schema.device import ServiceDetailBaseDeviceSchema
from app.schema.paginator import BasePaginator

logger = logging.getLogger(__name__)


class OMDeviceSchema(ServiceDetailBaseDeviceSchema):
    next_scheduled_service_date: ClassVar
    id: int
    asset_id: Optional[str] = Field(examples=["1344ASD12"])
    name: str = Field(examples=["Basic Inverter"])
    type: Optional[DeviceTypes] = Field(examples=[DeviceTypes.micro_inverter])
    category: DeviceCategories = Field(examples=[DeviceCategories.inverter])
    last_reported: Optional[str] = Field(None, examples=["12 min"])
    alerts_overview: Optional[Union[AlertOverviewSchema, dict]] = Field(default={"total": 0, "severity": None})
    das_connection_status: str = Field(examples=["Connected"])
    status: DeviceStatuses


class OMDeviceListPaginator(BasePaginator):
    items: List[OMDeviceSchema]


class TelemetryStaticDeviceData(BaseModel):
    """Schema for telemetry static device data validation"""

    category: Optional[str] = Field(None, examples=[DeviceCategories.inverter], validate_default=True)
    asset_id: Optional[str] = Field(examples=["1344ASD12"])
    name: Optional[str] = Field(examples=["Telemetry device"])
    type: Optional[str] = Field(None, validate_default=True)
    serial_number: Optional[str] = Field(None, examples=["1344ASD12"])
    gateway_id: Optional[str] = Field(None, examples=["1344ASD12"])
    function_id: Optional[str] = Field(None, examples=["1344A3232SD12"])
    driver: Optional[str] = Field(None, examples=["driver"])
    last_updated_date: Optional[str | datetime] = Field(None, examples=["2024-12-13T15:03:42.814484+00:00"])

    @field_validator("last_updated_date")
    @classmethod
    def validate_last_updated(cls, last_updated_date):
        if last_updated_date:
            try:
                return datetime.fromisoformat(last_updated_date)
            except ValueError as date_format_error:
                logger.warning(
                    f"Received invalid `last_updated_date`={last_updated_date} from BigQuery - ignoring this field. "
                    f"{date_format_error}"
                )

    @field_validator("category")
    @classmethod
    def validate_category(cls, category):
        if category:
            try:
                return DeviceCategories(category)
            except ValueError:
                available_categories = ", ".join([d.value for d in DeviceCategories])
                logger.warning(
                    f"Received invalid `category`={category} from BigQuery - ignoring this field. "
                    f"Validation error: Input should be one of '{available_categories}'"
                )
