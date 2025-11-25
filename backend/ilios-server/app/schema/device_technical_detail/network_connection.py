from typing import Optional

from pydantic import BaseModel, Field


class NetworkConnectionTechnicalDetailsSchema(BaseModel):
    provider: Optional[str] = Field(None, examples=["Photovoltaic systems"], title="Provider", max_length=100)
    account_number: Optional[str] = Field(None, examples=["22144917"], title="Account #", max_length=100)
