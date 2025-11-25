"""API Schema for site-related endpoints in O&M module"""

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.schema.alert import AlertOverviewSchema
from app.schema.common import calculate_actual_vs_expected, round_to_scale_2
from app.schema.paginator import BasePaginator


class OMSitesBaseSchema(BaseModel):
    id: int
    name: str = Field(examples=["Green day"])
    actual_kw: Optional[float] = Field(examples=[12300])
    expected_kw: Optional[float] = Field(examples=[22400])

    _round_capacity_to_scale_2 = field_validator("actual_kw", "expected_kw")(round_to_scale_2)


class CumulativeProductionDetailsBaseSchema(BaseModel):
    cumulative_actual_kw: Optional[float] = Field(0, examples=[123])
    cumulative_expected_kw: Optional[float] = Field(0, examples=[224])
    cumulative_actual_vs_expected: Optional[float] = Field(0, validate_default=True, examples=[22])
    cumulative_performance_index: Optional[float] = Field(None, validate_default=True, examples=[2.0])

    _round_cumulative_to_scale_2 = field_validator("cumulative_actual_kw", "cumulative_expected_kw")(round_to_scale_2)

    @field_validator("cumulative_actual_vs_expected")
    @classmethod
    def calculate_cumulative_actual_vs_expected(cls, cumulative_actual_vs_expected, info):  # noqa: U100
        actual_kw = info.data.get("cumulative_actual_kw")
        expected_kw = info.data.get("cumulative_expected_kw")
        return calculate_actual_vs_expected(actual_kw, expected_kw)

    @field_validator("cumulative_performance_index")
    @classmethod
    def calculate_cumulative_performance_index(cls, cumulative_performance_index, info):  # noqa: U100
        return info.data.get("cumulative_actual_vs_expected", 0) / 100


class WeatherSchema(BaseModel):
    weather_description: str
    weather_icon_url: str


class OMSitesBaseExtendedSchema(OMSitesBaseSchema):
    # TODO: remove default value after frontend replaces weather with WeatherSchema, until that return "N/A"
    latest_weather_info: Optional[WeatherSchema | str] = Field(
        None, validate_default=True, examples=["Sunny"], serialization_alias="weather"
    )
    actual_vs_expected: Optional[int] = Field(None, validate_default=True, examples=[22])

    @field_validator("actual_vs_expected")
    @classmethod
    def generate_actual_vs_expected(cls, actual_vs_expected, info):  # noqa: U100
        actual_kw = info.data.get("actual_kw")
        expected_kw = info.data.get("expected_kw")
        return calculate_actual_vs_expected(actual_kw, expected_kw)

    @field_validator("latest_weather_info")
    @classmethod
    def generate_weather(cls, weather):
        return "N/A" if weather is None else weather


class OMSitesPageSchema(OMSitesBaseExtendedSchema):
    cumulative_vs_expected: Optional[int] = Field(None, validate_default=True, examples=[43])
    cumulative_7_days_vs_expected: Optional[int] = Field(None, validate_default=True, examples=[65])
    cumulative_30_days_vs_expected: Optional[int] = Field(None, validate_default=True, examples=[98])
    alerts_overview: Optional[Union[AlertOverviewSchema, dict]] = Field(default={"total": 0, "severity": None})
    das_connection_status: str = Field(examples=["Connected"])


class OMSitesPaginator(BasePaginator):
    """Companies schema along pagination fields included, for the O&M module."""

    items: list[OMSitesPageSchema]


class OMSiteCompanyDashboardChartSchema(OMSitesBaseSchema):
    # field is needed for AG Grid lib to support this type of chart
    size: Optional[float] = Field(examples=[1], default=1)


class OMSiteDeviceDashboardData(BaseModel):
    device_type: str = Field(examples=["Inverter"], description="Device category name")
    devices: int = Field(examples=[1], description="Number of devices")
    critical_errors: int = Field(examples=[1], description="Number of non-resolved critical errors")
    # TODO remove default
    no_respond: int = Field(
        default=0, examples=[1], description="Number of no respond devices if applicable for the category"
    )


class OMSiteDeviceDashboardDataList(BaseModel):
    data: list[OMSiteDeviceDashboardData]


class OMSiteInverterPerformanceSchema(BaseModel):
    name: str
    actual: Optional[Union[float, str]] = Field(0, examples=[12300])
    expected: Optional[Union[float, str]] = Field(0, examples=[22400])
    performance: Optional[Union[int, str]] = Field(
        default=0, examples=[97], description="Int for the mapped devices, N/A for not mapped"
    )

    @field_validator("actual", "expected")
    @classmethod
    def round_actual_expected(cls, field_value):
        """If actual/expected value is numeric, round it to scale 2. Otherwise, return it as is."""
        if isinstance(field_value, float):
            return round_to_scale_2(field_value)
        return field_value


class OMSiteInvertersPerformanceListSchema(BaseModel):
    data: list[OMSiteInverterPerformanceSchema]


class SiteDashboardActualProductionSection(OMSitesBaseExtendedSchema, CumulativeProductionDetailsBaseSchema):
    # Exclude fields from this section as presented on top in response
    id: int = Field(exclude=True)
    name: str = Field(exclude=True)

    system_size_ac: float
    system_size_dc: float
    performance_index: Optional[float] = Field(None, validate_default=True, examples=[2.0])

    _round_system_sizes_to_scale_2 = field_validator("system_size_ac", "system_size_dc")(round_to_scale_2)

    @field_validator("performance_index")
    @classmethod
    def generate_performance_index(cls, performance_index, info):  # noqa: U100
        """Calculate performance_index based on actual_vs_expected generated in the parent schema"""
        return info.data.get("actual_vs_expected", 0) / 100


class OMSitePastPerformanceSchema(BaseModel):
    data: dict[datetime, int]


class SiteActualVSExpectedPerformance(BaseModel):
    period: datetime
    actual: float
    expected: float
    irradiance: float


class SiteActualVSExpectedPerformanceListSchema(BaseModel):
    data: list[SiteActualVSExpectedPerformance]


class OMSiteSchema(BaseModel):
    """Site dashboard schema for the O&M module."""

    id: int
    name: str


# Investor Dashboard details


class InvestorDashboardSiteSchema(OMSitesPageSchema):
    alerts_overview: Optional[str] = Field(None, exclude=True)


class InvestorDashboardSitesPaginator(BasePaginator):
    items: list[InvestorDashboardSiteSchema]


class SiteLocationSchema(BaseModel):
    id: int
    location: str = Field(validation_alias="lon_lat_url")


class SitesLocationsList(BaseModel):
    data: Optional[list[SiteLocationSchema]]


class SiteWeatherSchema(WeatherSchema):
    site_id: int


class CreateSiteWeatherList(BaseModel):
    payload: Optional[list[SiteWeatherSchema]]
