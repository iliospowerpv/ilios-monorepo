from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from app.schema.device_technical_detail.common import YesNoDropdown


class RackMountGeneralSectionSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    racking_capacity: Optional[float] = Field(None, examples=[11.11], title="Racking Capacity (kWp DC)")
    azimuth: Optional[float] = Field(None, examples=[11.22], title="Azimuth (degrees)")
    tracking: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.yes], title="Tracking")


class RachMountTechnicalDetailsSchema(BaseModel):
    general: Optional[SerializeAsAny[RackMountGeneralSectionSchema]] = Field(
        default=RackMountGeneralSectionSchema().model_dump(),
        title="General",
    )
