"""Company validation schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.site import State
from app.schema.common import SuccessUpdateSchema, round_to_scale_2
from app.schema.paginator import BasePaginator
from app.static.companies import CompanyTypes


class BaseCompanyPageSchema(BaseModel):
    """Base schema for objects in company scope."""

    id: int = Field(examples=[1])
    name: str = Field(examples=["Green Lantern"])


class UpsertCompanySchema(BaseModel):
    """Company upsert schema (upsert = insert + update)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(examples=["Green Lantern"], min_length=2, max_length=100)
    email: Optional[EmailStr] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, examples=["0123456789"], min_length=10, max_length=20)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, v):
        if v is None:
            return v
        import re
        digits = re.sub(r"\D", "", v)
        if digits.startswith("1") and len(digits) == 11:
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("Phone number must contain exactly 10 digits")
        return digits

    address: Optional[str] = Field(None, examples=["719 Main Street Solar"], max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[State] = Field(None)
    county: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, pattern=r"^[0-9]+$", max_length=5)


class CreateCompanySchema(UpsertCompanySchema):
    company_type: CompanyTypes
    name: str = Field(examples=["Green Lantern"], min_length=2, max_length=100)
    address: str = Field(examples=["719 Main Street Solar"], max_length=255)
    city: str = Field(examples=["Mullica Hill"], max_length=100)
    state: State
    zip_code: str = Field(pattern=r"^[0-9]+$", examples=["08062"], max_length=5)


class CompanySchema(UpsertCompanySchema):
    """Full company schema for responses. Address fields are optional since older records may not have them."""

    id: int = Field(examples=[1])
    company_type: CompanyTypes


class CompanySchemaSitesInfo(CompanySchema):
    total_sites: int = Field(examples=[1])
    sites_placed_in_service: int = Field(examples=[1])
    sites_under_construction: int = Field(examples=[0])
    sites_decommissioned: int = Field(examples=[0])
    sites_sold: int = Field(examples=[0])
    total_capacity: float = Field(examples=[27500.0])

    _round_capacity_to_scale_2 = field_validator("total_capacity")(round_to_scale_2)


class CompaniesPageSchema(BaseCompanyPageSchema):
    """Model of fields for the page of companies listing."""

    total_sites: int = Field(examples=[3])
    total_capacity: float = Field(examples=[15000.0])
    is_archived: bool = Field(default=False)

    _round_capacity_to_scale_2 = field_validator("total_capacity")(round_to_scale_2)


class CompaniesOrderByFieldEnum(str, Enum):
    """Model of fields enumeration allowed for order_by query param possible values."""

    id = "id"
    name = "name"
    total_sites = "total_sites"
    total_capacity = "total_capacity"


class CompaniesPaginator(BasePaginator):
    """Companies schema along pagination fields included, for the asset management module."""

    items: list[CompaniesPageSchema]


class ContractorsPaginator(BasePaginator):
    """Contractors schema along pagination fields included."""

    items: list[CompanySchema]


class ContractorsOrderByFieldEnum(str, Enum):
    """Model of fields enumeration allowed for order_by query param possible values."""

    name = "name"
    company_type = "company_type"
    address = "address"
    email = "email"


class CompanySite(BaseModel):
    """Model of fields for the included company site."""

    id: int = Field(examples=[1])
    name: str = Field(examples=["Apollo"])


class CompanyWithSitesSchema(BaseCompanyPageSchema):
    """Model of fields for company sites."""

    sites: list[CompanySite]


class CompanyListSiteSchema(BaseModel):
    """Model of fields for company sites."""

    data: list[CompanyWithSitesSchema]


class CompanyCreationSuccess(BaseModel):
    id: int = Field(examples=[1])
    message: str = Field(description="Success message", examples=["Company has been successfully created"])
    code: int = Field(description="Success status code", examples=[201])


class CompanyUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["Company has been updated successfully"])


class ReportCompaniesOrderByFieldEnum(str, Enum):

    id = "id"
    name = "name"


class ReportsCompaniesPaginator(BasePaginator):

    items: list[BaseCompanyPageSchema]
