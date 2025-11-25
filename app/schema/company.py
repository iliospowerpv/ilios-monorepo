"""Company validation schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
    phone: Optional[str] = Field(None, pattern=r"^[0-9]+$", examples=["0123456789"], min_length=10, max_length=10)
    address: Optional[str] = Field(None, examples=["719 Main Street Solar"], max_length=255)


class CreateCompanySchema(UpsertCompanySchema):
    company_type: CompanyTypes


class CompanySchema(CreateCompanySchema):
    """Full company schema."""

    id: int = Field(examples=[1])


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
    message: str = Field(description="Success message", examples=["Company has been successfully created"])
    code: int = Field(description="Success status code", examples=[201])


class CompanyUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["Company has been updated successfully"])


class ReportCompaniesOrderByFieldEnum(str, Enum):

    id = "id"
    name = "name"


class ReportsCompaniesPaginator(BasePaginator):

    items: list[BaseCompanyPageSchema]
