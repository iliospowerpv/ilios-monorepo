from typing import Optional

from pydantic import BaseModel, Field

from app.schema.device_technical_detail.common import IPAddressSchema


class NetworkGatewayTechnicalDetailsSchema(BaseModel):
    communication: Optional[IPAddressSchema] = Field(default=IPAddressSchema().model_dump(), title="Communication")
