from typing import Optional

from pydantic import BaseModel, Field


class CombinerBoxTechnicalDetailsSchema(BaseModel):
    enclosure_type: Optional[str] = Field(
        None, examples=["IP68 waterproof enclosure with ventilation plug"], title="Enclosure Type", max_length=100
    )
    dimensions: Optional[str] = Field(None, examples=["12 x 44 x 14"], title="Dimensions", max_length=100)
    weight: Optional[float] = Field(None, examples=[1.01], title="Weight (lbs)")
    max_output: Optional[float] = Field(None, examples=[1.02], title="Max Output")
    input_circuits_max_count: Optional[float] = Field(None, examples=[1.32], title="Max # of Input Circuits")
