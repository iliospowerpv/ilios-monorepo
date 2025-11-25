from typing import Optional

from pydantic import BaseModel, Field, SerializeAsAny

from app.schema.device_technical_detail.common import IPAddressSchema


class MeterGeneralSectionSchema(BaseModel):
    capacity: Optional[float] = Field(None, examples=[4606], title="Capacity kW")
    inverters: Optional[float] = Field(None, examples=[990], title="Inverters kW")


class MeterCommunicationSectionSchema(IPAddressSchema):
    unit_id: Optional[int] = Field(None, examples=[1], title="Unit ID")


class MeterScaleFactorSectionSchema(BaseModel):
    power: Optional[float] = Field(None, examples=[1], title="Power Scale Factor")
    energy: Optional[float] = Field(None, examples=[1], title="Energy Scale Factor")
    swap_delivered_received: Optional[str] = Field(
        None, examples=["Yes"], title="Swap Delivered and Received", max_length=100
    )
    gross_energy: Optional[str] = Field(None, examples=["Undefined"], title="Gross energy", max_length=100)


class MeterSampleDataSectionSchema(BaseModel):
    kw: Optional[float] = Field(None, examples=[964.8883498956832], title="kW")
    kwh_net: Optional[float] = Field(None, examples=[6585320], title="kWh Net")
    kwh_received: Optional[float] = Field(None, examples=[6628503], title="kWh Received")
    kwh_delivered: Optional[float] = Field(None, examples=[4434554434], title="kWh Delivered")


class MeterDataRangeSectionSchema(BaseModel):
    max_power: Optional[float] = Field(None, examples=[2806], title="Max power, kW")
    max_voltage: Optional[float] = Field(None, examples=[480], title="Max Voltage")
    max_current_per_phase: Optional[float] = Field(None, examples=[5850], title="Max Current (per phase)")
    ac: Optional[str] = Field(None, examples=["Wye"], title="AC", max_length=100)


class MeterTechnicalDetailsSchema(BaseModel):
    general: Optional[SerializeAsAny[MeterGeneralSectionSchema]] = Field(
        default=MeterGeneralSectionSchema().model_dump(),
        title="General",
    )
    communication: Optional[SerializeAsAny[MeterCommunicationSectionSchema]] = Field(
        default=MeterCommunicationSectionSchema().model_dump(), title="Communication"
    )
    scale_factor: Optional[SerializeAsAny[MeterScaleFactorSectionSchema]] = Field(
        default=MeterScaleFactorSectionSchema().model_dump(), title="Scale Factor"
    )
    sample_date: Optional[SerializeAsAny[MeterSampleDataSectionSchema]] = Field(
        default=MeterSampleDataSectionSchema().model_dump(), title="Sample Data"
    )
    data_range: Optional[SerializeAsAny[MeterDataRangeSectionSchema]] = Field(
        default=MeterDataRangeSectionSchema().model_dump(), title="Data Range"
    )
