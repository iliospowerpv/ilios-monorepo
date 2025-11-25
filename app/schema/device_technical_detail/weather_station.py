from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schema.device_technical_detail.common import CommunicationSectionSchema, YesNoDropdown


class WeatherStationSensorsSectionSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    wind: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.yes], title="Wind")
    humidity: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.no], title="Humidity")
    barometer: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.no], title="Barometer")
    snow_depth: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.no], title="Snow Depth")
    normal_incidence_pyrheliometer: Optional[YesNoDropdown] = Field(
        None, examples=[YesNoDropdown.no], title="Normal Incidence Pyrheliometer"
    )
    rain: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.no], title="Rain")
    temperature: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.yes], title="Temperature")
    irradiance: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.yes], title="Irradiance")


class WeatherStationTemperatureSensorsSectionSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    ambient_temperature: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.yes], title="Ambient Temperature")
    panel_temperature1: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.no], title="Panel Temperature 1")
    panel_temperature2: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.no], title="Panel Temperature 1")
    min_temperature: Optional[float] = Field(None, examples=[-30], title="Minimum Temperature")
    max_temperature: Optional[float] = Field(None, examples=[160], title="Maximum Temperature")


class WeatherStationPyranometerSensorsSectionSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    reference: Optional[YesNoDropdown] = Field(None, examples=[YesNoDropdown.no], title="Reference Pyranometer (GHI)")
    azimuth_and_tilt: Optional[YesNoDropdown] = Field(
        None, examples=[YesNoDropdown.yes], title="Pyranometer (Azimuth & Tilt)"
    )
    azimuth: Optional[float] = Field(None, examples=[180], title="Pyranometer Azimuth")
    tilt: Optional[float] = Field(None, examples=[30], title="Pyranometer Tilt")
    tracking: Optional[str] = Field(None, examples=["Fixed"], title="Tracking", max_length=100)
    pyranometer: Optional[str] = Field(
        None, examples=["Normal limits (below 1200 W/m)"], title="Pyranometer", max_length=100
    )


class WeatherStationMonthlyInsolationSensorsSectionSchema(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    january: Optional[float] = Field(None, examples=[62], title="January")
    february: Optional[float] = Field(None, examples=[84], title="February")
    march: Optional[float] = Field(None, examples=[124], title="March")
    april: Optional[float] = Field(None, examples=[150], title="April")
    may: Optional[float] = Field(None, examples=[186], title="May")
    june: Optional[float] = Field(None, examples=[180], title="June")
    july: Optional[float] = Field(None, examples=[186], title="July")
    august: Optional[float] = Field(None, examples=[186], title="August")
    september: Optional[float] = Field(None, examples=[150], title="September")
    october: Optional[float] = Field(None, examples=[93], title="October")
    november: Optional[float] = Field(None, examples=[60], title="November")
    december: Optional[float] = Field(None, examples=[62], title="December")
    insolation_reference: Optional[str] = Field(
        None, examples=["Global horizontal"], title="Insolation Reference", max_length=100
    )
    interpolate_daily_insolation: Optional[YesNoDropdown] = Field(
        None, examples=[YesNoDropdown.yes], title="Interpolate Daily Insolation"
    )


class WeatherStationTechnicalDetailsSchema(BaseModel):
    communication: Optional[CommunicationSectionSchema] = Field(
        default=CommunicationSectionSchema().model_dump(), title="Communication"
    )
    sensors: Optional[WeatherStationSensorsSectionSchema] = Field(
        default=WeatherStationSensorsSectionSchema().model_dump(), title="Sensors"
    )
    temperature_sensors: Optional[WeatherStationTemperatureSensorsSectionSchema] = Field(
        default=WeatherStationTemperatureSensorsSectionSchema().model_dump(), title="Temperature Sensors"
    )
    pyranometer_sensors: Optional[WeatherStationPyranometerSensorsSectionSchema] = Field(
        default=WeatherStationPyranometerSensorsSectionSchema().model_dump(), title="Pyranometer Sensors"
    )
    monthly_insolation: Optional[WeatherStationMonthlyInsolationSensorsSectionSchema] = Field(
        default=WeatherStationMonthlyInsolationSensorsSectionSchema().model_dump(), title="Monthly Insolation (kWh/m)"
    )
