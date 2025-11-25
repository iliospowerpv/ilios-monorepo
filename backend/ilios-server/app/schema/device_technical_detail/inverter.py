from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from app.schema.device_technical_detail.common import CommunicationSectionSchema, YesNoDropdown


class InverterPowerSectionViewSchema(BaseModel):
    dc_power: Optional[float] = Field(None, examples=[1.11], title="DC Power (kW)")
    dc_max_input: Optional[float] = Field(None, examples=[1.12], title="DC Max Input Voltage (V)")
    ac_power: Optional[float] = Field(None, examples=[1.13], title="AC Power (kW)")
    ac_max_output: Optional[float] = Field(None, examples=[1.14], title="AC Max Output Voltage (V)")
    standby_power: Optional[float] = Field(None, examples=[1.15], title="Standby Power (Watts)")
    rated_output: Optional[float] = Field(None, examples=[1.16], title="Rated Output (kVA)")
    cec_efficiency: Optional[float] = Field(None, examples=[98.4], title="CEC Efficiency (%)")
    pv_modules_number: Optional[float] = Field(None, examples=[30], title="Number of PV modules per Inverter")


class InverterPowerSectionUpdateSchema(InverterPowerSectionViewSchema):
    cec_efficiency: float = Field(examples=[98.4], title="CEC Efficiency (%)")
    pv_modules_number: float = Field(examples=[30], title="Number of PV modules per Inverter")


class InverterArraySectionSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    number_of_strings: Optional[float] = Field(None, examples=[3.11], title="Number of Strings")
    modules_per_string: Optional[float] = Field(None, examples=[3.12], title="Modules per String")
    integrated_combiners: Optional[YesNoDropdown] = Field(
        None, examples=[YesNoDropdown.yes], title="Integrated Combiners"
    )
    yearly_degradation: Optional[float] = Field(None, examples=[3.13], title="Yearly Degradation")
    derate: Optional[float] = Field(None, examples=[3.14], title="Derate")


class InverterModuleSectionSchema(BaseModel):
    watts_per_module: Optional[float] = Field(None, examples=[4.11], title="Watts per Module")
    mpp_voltage: Optional[float] = Field(None, examples=[4.12], title="MPP Voltage")
    mpp_current: Optional[float] = Field(None, examples=[4.13], title="MPP Current")
    mpp_watts: Optional[float] = Field(None, examples=[4.14], title="MPP Watts")
    temperature_coefficient: Optional[float] = Field(None, examples=[4.15], title="Temperature Coefficient (%)")


class InverterTechnicalDetailsViewSchema(BaseModel):
    power: Optional[SerializeAsAny[InverterPowerSectionViewSchema]] = Field(
        default=InverterPowerSectionViewSchema().model_dump(),
        title="Power",
        examples=[InverterPowerSectionViewSchema().model_dump()],
    )
    communication: Optional[SerializeAsAny[CommunicationSectionSchema]] = Field(
        default=CommunicationSectionSchema().model_dump(), title="Communication"
    )
    array: Optional[SerializeAsAny[InverterArraySectionSchema]] = Field(
        default=InverterArraySectionSchema().model_dump(), title="Array"
    )
    module: Optional[SerializeAsAny[InverterModuleSectionSchema]] = Field(
        default=InverterModuleSectionSchema().model_dump(), title="Module"
    )


class InverterTechnicalDetailsUpdateSchema(InverterTechnicalDetailsViewSchema):
    power: Optional[SerializeAsAny[InverterPowerSectionUpdateSchema]] = Field(
        title="Power",
        examples=[InverterPowerSectionViewSchema().model_dump()],
    )
