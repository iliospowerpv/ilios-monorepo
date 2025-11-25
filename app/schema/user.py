"""Company validation schemas."""

from enum import Enum
from typing import ClassVar, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schema.common import SuccessUpdateSchema
from app.schema.company import CompanySchema
from app.schema.paginator import BasePaginator
from app.schema.role import RoleWithPermissions
from app.schema.site import MinimalisticSiteSchema


class UserEmailSchema(BaseModel):
    email: EmailStr = Field(max_length=100)

    @field_validator("email", mode="before")
    @classmethod
    def lower_case_email(cls, email_address):
        return email_address.lower()


class CurrentUserSchema(UserEmailSchema):

    id: int = Field(1)


class UserRole(BaseModel):
    name: str


class ListUserSchema(CurrentUserSchema):

    first_name: str = Field(..., examples=["Will"])
    last_name: str = Field(..., examples=["Smith"])
    role: Optional[UserRole] = Field(..., examples=["Administrator"])
    is_registered: bool = Field(examples=[True])
    parent_company_id: Optional[int] = Field(examples=[1])
    phone: str = Field(examples=["0123456789"])


class UsersListResponse(BasePaginator):

    items: list[ListUserSchema]


class BaseUserSchema(UserEmailSchema):
    parent_company_id: Optional[int] = Field(examples=[1])
    role_id: Optional[int] = Field(examples=[1])
    phone: str = Field(pattern=r"^[0-9]+$", examples=["0123456789"], min_length=10, max_length=10)
    first_name: str = Field(examples=["Jane"], min_length=2, max_length=100)
    last_name: str = Field(examples=["Doe"], min_length=2, max_length=100)


class MyUserSchema(BaseUserSchema):
    role: Optional[RoleWithPermissions]
    sites: list[MinimalisticSiteSchema]
    is_system_user: Optional[bool] = Field(examples=[True])
    diligence_overview_access: bool = Field(examples=[True])


class GetUserSchema(MyUserSchema):
    # exclude since we return full object
    role_id: ClassVar[int]
    parent_company_id: ClassVar[int]
    diligence_overview_access: ClassVar[bool]
    parent_company: CompanySchema | None = Field(
        examples=[
            {
                "name": "Global Company",
                "email": "no-reply@example.com",
                "phone": "1234567890",
                "address": "Green Street 123",
                "id": 1,
            }
        ]
    )


class CreateUserSchema(BaseUserSchema):

    sites_ids: list[int] = Field(examples=[[4, 5, 15]], min_length=1)


class EditUserSchema(UserEmailSchema):
    phone: str = Field(pattern=r"^[0-9]+$", examples=["0123456789"], min_length=10, max_length=10)
    role_id: int = Field(examples=[1])
    parent_company_id: int = Field(examples=[1])
    sites_ids: list[int] = Field(min_length=1, examples=[[1, 2, 3]])


class UserCreationSuccess(BaseModel):
    message: str = Field(description="Success message", examples=["A new user Jane Doe was added"])
    code: int = Field(description="Success status code", examples=[201])


class UserUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["User Jane Doe was updated"])


class UserResendInvitationSuccess(BaseModel):
    message: str = Field(description="Success message", examples=["The registration email has been resent"])
    code: int = Field(description="Success status code", examples=[201])


class InvitationTokenValidationSuccess(BaseModel):
    message: str = Field(description="Success message", examples=["Token is valid"])
    code: int = Field(description="Success status code", examples=[200])


class UserOrderByFieldEnum(str, Enum):
    """Model of fields enumeration allowed for order_by query param possible values."""

    first_name = "first_name"
    last_name = "last_name"
    email = "email"
    role = "role"


class AccountMgmtModeEnum(str, Enum):
    sign_up: str = "sign-up"
    recovery: str = "recovery"
