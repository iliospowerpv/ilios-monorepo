from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schema.common import date_field_validator
from app.schema.message import Success
from app.static import TEXT_AREA_MAX_LENGTH, TEXT_FIELD_MAX_LENGTH, TaskMessages


class SiteVisitStatusEnum(str, Enum):
    resolved = "Resolved"
    escalated = "Escalated"
    rma = "RMA"


class SiteVisitCreationSuccess(Success):
    message: str = Field(description="Success message", examples=[TaskMessages.site_visit_create_success])


class SiteVisitUpdateSuccess(Success):
    message: str = Field(description="Success message", examples=[TaskMessages.site_visit_update_success])


class SiteVisitSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    service_date: Optional[date] = Field(default=None, examples=["2025-02-11"])
    technician_assignee: Optional[str] = Field(default=None, examples=["Joe Fr. Doe"], max_length=TEXT_FIELD_MAX_LENGTH)
    reasons: Optional[str] = Field(default=None, examples=["Annual devices check"], max_length=TEXT_AREA_MAX_LENGTH)
    scope_of_work: Optional[str] = Field(
        default=None, examples=["Ensure all devices are connected properly"], max_length=TEXT_AREA_MAX_LENGTH
    )
    status: Optional[SiteVisitStatusEnum] = Field(default=None, examples=[SiteVisitStatusEnum.resolved])
    resolution: Optional[str] = Field(
        default=None, examples=["Yearly maintenance goes smoothly"], max_length=TEXT_AREA_MAX_LENGTH
    )
    next_steps: Optional[str] = Field(
        default=None, examples=["Update device #3 in 2 months"], max_length=TEXT_AREA_MAX_LENGTH
    )
    pending_work: Optional[str] = Field(
        default=None, examples=["Device #3 replacement"], max_length=TEXT_AREA_MAX_LENGTH
    )
    recommendations: Optional[str] = Field(
        default=None, examples=["Follow the suggested maintenance schedule"], max_length=TEXT_AREA_MAX_LENGTH
    )

    _validate_date = field_validator("service_date", mode="before")(date_field_validator)
