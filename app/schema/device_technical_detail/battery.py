from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schema.common import date_field_validator
from app.schema.device_technical_detail.common import YesNoDropdown


class BatteryTechnicalDetailsSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    size_kw: Optional[float] = Field(None, examples=[1.123], title="Battery Size (kW - AC)")
    size_mwh: Optional[float] = Field(None, examples=[1.274], title="Battery Size (MWh - AC)")
    report: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.yes], title="Smart ESS Annual Report")
    report_due_date: Optional[date] = Field(
        default=None, examples=["2025-06-19"], title="Smart ESS Annual Report Due Date"
    )

    _validate_date = field_validator("report_due_date", mode="before")(date_field_validator)
