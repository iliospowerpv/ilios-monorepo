from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class BQDeviceCharacteristicsUpdateSchema(BaseModel):
    """Combination of fields for Inverter and Module devices"""

    # inverter fields
    cec_efficiency: Optional[float] = Field(None, examples=[98.4])
    number_of_pv_modules_per_inverter: Optional[int] = Field(None, examples=[30])
    # module fields
    thermal_coefficient_of_power: Optional[float] = Field(None, examples=[-0.35])
    power_tolerance_min: Optional[float] = Field(None, examples=[0])
    power_tolerance_max: Optional[float] = Field(None, examples=[5])
    year_1_degradation: Optional[float] = Field(None, examples=[2])
    annual_degradation: Optional[float] = Field(None, examples=[0.54])


class BQDeviceCharacteristicsCreateSchema(BQDeviceCharacteristicsUpdateSchema):
    site_id: int = Field(examples=[42])
    device_id: int = Field(examples=[15])
    device_category: str = Field(examples=["inverter"])


class BQSiteCharacteristicsUpdateSchema(BaseModel):
    """Combination of Asset and DD modules fields"""

    # DD fields
    module_wattage: Optional[int] = Field(None, examples=[400])
    module_quantity: Optional[int] = Field(None, examples=[10])
    inverter_wattage: Optional[int] = Field(None, examples=[100])
    inverter_quantity: Optional[int] = Field(None, examples=[4])
    # aggregated year 1 production
    estimated_generation: Optional[list] = Field(None, examples=[[10, 12.5, 24, 34, 43, 50, 55, 58, 60, 40, 35, 28]])
    # Asset fields
    permission_to_operate: Optional[date] = Field(None, examples=["2025-08-20"])
    dc_ohmic_wiring_loss: Optional[float] = Field(None, examples=[0.58])
    ac_ohmic_wiring_loss: Optional[float] = Field(None, examples=[-0.71])
    medium_voltage_transfo_loss: Optional[float] = Field(None, examples=[-1.35])
    mv_line_ohmic_loss: Optional[float] = Field(None, examples=[-0.01])


class BQSiteCharacteristicsCreateSchema(BQSiteCharacteristicsUpdateSchema):
    site_id: int = Field(examples=[17])
