"""API Schema for device-related Endpoints"""

from typing import Optional

from pydantic import BaseModel, Field, SerializeAsAny


class ModuleSpecsSectionSchema(BaseModel):
    weight: Optional[float] = Field(None, examples=[1.0], title="Weight (lbs)")
    module_kw: Optional[float] = Field(None, examples=[1.1], title="Module kW")
    solar_cells_per_module: Optional[float] = Field(None, examples=[1.2], title="Solar Cells per Module")
    solar_cell_type: Optional[str] = Field(
        None, examples=["Concentrated Photovoltaic (CPV)"], title="Solar Cell Type", max_length=100
    )
    glass_type: Optional[str] = Field(None, examples=["Borosilicate"], title="Glass Type", max_length=100)
    cable_and_connector: Optional[str] = Field(
        None, examples=["MC4 connectors"], title="Cable & Connector", max_length=100
    )
    frame: Optional[str] = Field(None, examples=["Origami Solar’s"], title="Frame", max_length=100)


class ModulePowerSectionViewSchema(BaseModel):
    system_voltage: Optional[float] = Field(None, examples=[2.11], title="System Voltage (V)")
    power_output: Optional[float] = Field(None, examples=[2.12], title="Power Output (W)")
    mpp_voltage: Optional[float] = Field(None, examples=[2.13], title="MPP Voltage")
    mpp_current: Optional[float] = Field(None, examples=[2.14], title="MPP Current")
    mpp_watts: Optional[float] = Field(None, examples=[2.15], title="MPP Watts")
    temperature_coefficient: Optional[float] = Field(None, examples=[2.16], title="Temperature Coefficient (%)")
    watts_per_module: Optional[float] = Field(None, examples=[2.17], title="Watts per Module")
    max_power_tolerance: Optional[float] = Field(None, examples=[5], title="Power Tolerance Max (W)")
    min_power_tolerance: Optional[float] = Field(None, examples=[0], title="Power Tolerance Min (W)")
    power_thermal_coefficient: Optional[float] = Field(None, examples=[-0.35], title="Thermal Coefficient of Power (%)")
    year_1_degradation: Optional[float] = Field(None, examples=[2], title="Year 1 Degradation %")
    annual_degradation: Optional[float] = Field(None, examples=[0.54], title="Annual Degradation %")


class ModulePowerSectionUpdateSchema(ModulePowerSectionViewSchema):
    # needs to be required while edited
    max_power_tolerance: float = Field(examples=[5], title="Power Tolerance Max (W)", ge=0)
    min_power_tolerance: float = Field(examples=[0], title="Power Tolerance Min (W)", le=0)
    power_thermal_coefficient: float = Field(examples=[-0.35], title="Thermal Coefficient of Power (%)")
    year_1_degradation: float = Field(examples=[2], title="Year 1 Degradation %")
    annual_degradation: float = Field(examples=[0.54], title="Annual Degradation %")


class ModuleTechnicalDetailsViewSchema(BaseModel):
    module_specs: Optional[SerializeAsAny[ModuleSpecsSectionSchema]] = Field(
        default=ModuleSpecsSectionSchema().model_dump(),
        title="Module Specs",
        examples=[ModuleSpecsSectionSchema().model_dump()],
    )
    power: Optional[ModulePowerSectionViewSchema] = Field(
        default=ModulePowerSectionViewSchema().model_dump(),
        title="Power",
        examples=[ModulePowerSectionViewSchema().model_dump()],
    )


class ModuleTechnicalDetailsUpdateSchema(ModuleTechnicalDetailsViewSchema):
    power: Optional[ModulePowerSectionUpdateSchema] = Field(
        title="Power",
    )
