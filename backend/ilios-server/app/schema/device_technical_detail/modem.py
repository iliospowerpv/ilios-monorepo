from typing import Optional

from pydantic import BaseModel, Field

from app.schema.device_technical_detail.common import CommunicationSectionSchema


class ModemTechnicalDetailsSchema(BaseModel):
    communication: Optional[CommunicationSectionSchema] = Field(
        default=CommunicationSectionSchema().model_dump(), title="Communication"
    )
