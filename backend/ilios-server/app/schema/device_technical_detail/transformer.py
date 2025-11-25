from typing import Optional

from pydantic import BaseModel, Field


class TransformerTechnicalDetailsSchema(BaseModel):
    type: Optional[str] = Field(None, examples=["Three-phase pad mounted"], title="Type", max_length=100)
    rating: Optional[str] = Field(None, examples=["AAA"], title="Rating (kVA)", max_length=100)
    frequency: Optional[str] = Field(None, examples=["20 kHz - 1MHz"], title="Frequency", max_length=100)
    voltage: Optional[float] = Field(None, examples=[1.11], title="Primary Voltage")
    phase: Optional[str] = Field(None, examples=["Three"], title="Phase", max_length=100)
    volts: Optional[float] = Field(None, examples=[1.02], title="Volts")
