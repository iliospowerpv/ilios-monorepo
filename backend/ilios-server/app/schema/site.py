"""API Schema for site-related Endpoints"""

from datetime import date
from enum import Enum
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.site import SiteStatuses, State
from app.schema.common import SuccessUpdateSchema, round_to_scale_2
from app.schema.company import BaseCompanyPageSchema, CompanySchema
from app.schema.paginator import BasePaginator


class BaseSiteSchema(BaseModel):
    """Base API schema for site"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(examples=["Apollo"])
    address: str
    city: str
    state: State
    county: Optional[str] = Field(default=None)
    zip_code: str = Field(pattern=r"^[0-9]+$", examples=["01234"])
    system_size_ac: float
    system_size_dc: float
    lon_lat_url: str = Field(examples=["41° 56’ 54.3732"])
    cameras_uuids: Optional[list] = Field([], examples=[["ADDA12", "VDSDVS45"]])

    _round_system_sizes_to_scale_2 = field_validator("system_size_ac", "system_size_dc")(round_to_scale_2)

    @field_validator("zip_code")
    @classmethod
    def validate_zip_code(cls, zip_code):
        """Validate zip code length"""
        if len(zip_code) > 5:
            raise ValueError("zip code must be no longer than 5 digits.")
        return zip_code


class CreateSiteSchema(BaseSiteSchema):
    company_id: int = Field(examples=[1])
    model_config = ConfigDict(extra="forbid")


class UpdateSiteSchema(BaseSiteSchema):
    model_config = ConfigDict(extra="forbid")


class SiteCreationResponse(BaseModel):
    id: int = Field(examples=[1])
    message: str = Field(description="Success message", examples=["Site has been created"])
    code: int = Field(description="Success status code", examples=[201])


class ExtendedSiteSchema(BaseSiteSchema):
    """Extended site schema"""

    id: int = Field(examples=[1])
    company: CompanySchema = Field(
        examples=[
            {
                "name": "My Company",
                "email": "user@example.com",
                "phone": "458390964892744948805188",
                "address": "201 W 5th Street",
                "id": 1,
            }
        ]
    )

    @field_validator("state")
    @classmethod
    def reuse_object_value(cls, enum):
        """Overload to reuse Enum object value readable form"""
        return enum.value


class ExtendedSiteSchemaWithConnection(ExtendedSiteSchema):

    das_connection_name: Optional[str] = Field(examples=["KMC 1"])
    telemetry_site_name: Optional[str] = Field(examples=["Telemetry Site 1"])


class SiteListSchema(ExtendedSiteSchema):

    cameras_uuids: ClassVar

    # from site.additional_fields
    status: Optional[SiteStatuses] = Field(None, examples=["Placed In Service"])
    das_provider: Optional[str] = Field(None, examples=["DAS provider"], max_length=100)
    ownership_structure: Optional[str] = Field(None, examples=["Tax Equity Only"], max_length=100)
    placed_in_service_date: Optional[date] = Field(None, examples=["2020-01-04"])
    # from DD module
    production_guarantee: Optional[str] = Field(None, examples=["10 years"])
    o_and_m_provider: Optional[str] = Field(None, examples=["Big Bear PV, LLC"])
    utility_provider: Optional[str] = Field(None, examples=["Novel Caroline Solar LLC"])
    epc_provider: Optional[str] = Field(None, examples=["ANGEL’S CAMP PV, LLC"])


class MinimalisticSiteSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Apollo"])
    company: BaseCompanyPageSchema


class SiteOrderByFieldEnum(str, Enum):
    """Model of fields enumeration allowed for order_by query param possible values."""

    id = "id"
    company_id = "company_id"
    company_name = "company_name"
    name = "name"
    address = "address"
    city = "city"
    state = "state"
    county = "county"
    zip_code = "zip_code"
    lon_lat_url = "lon_lat_url"
    system_size_dc = "system_size_dc"
    system_size_ac = "system_size_ac"


class SiteSettingsOrderByFieldEnum(str, Enum):
    """Model of fields enumeration allowed for order_by query param possible values."""

    name = "name"
    address = "address"


class SiteSystemUserSettingsOrderByFieldEnum(str, Enum):
    """Model of fields enumeration allowed for order_by query param possible values."""

    name = "name"
    address = "address"
    company_name = "company_name"


class SitesSettingsSchema(BaseModel):
    id: int
    name: str
    address: str


class SitesSettingsList(BasePaginator):
    """Sites list for Settings page."""

    items: list[SitesSettingsSchema]


class SitesSystemUserSettings(SitesSettingsSchema):
    company_id: int
    company_name: str


class SitesSystemUserSettingsList(BasePaginator):
    """Sites list for Settings page."""

    items: list[SitesSystemUserSettings]


class AllSitesPaginator(BasePaginator):
    """All sites schema."""

    items: list[SiteListSchema]


class SiteUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["Site has been updated"])


class SiteActualExpectedPerformanceUpdate(BaseModel):
    actual_kw: float = Field(ge=0, le=50000)
    expected_kw: float = Field(ge=0, le=50000)


class PotentialTaskAssigneeSchema(BaseModel):
    id: int
    first_name: str
    last_name: str


class PotentialTaskAssigneeList(BaseModel):
    items: Optional[list[PotentialTaskAssigneeSchema]] = []


class PotentialAffectedDeviceSchema(BaseModel):
    id: int
    name: str


class PotentialAffectedDevicesList(BaseModel):
    items: Optional[list[PotentialAffectedDeviceSchema]] = []


class ReportsSiteOrderByFieldEnum(str, Enum):
    id = "id"
    name = "name"


class ReportSiteSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Apollo"])


class ReportSitesPaginator(BasePaginator):

    items: list[ReportSiteSchema]
