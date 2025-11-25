from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schema.paginator import BasePaginator


class AuditLogPageSchema(BaseModel):
    id: int = Field(examples=[1])
    user_name: str = Field(examples=["John Doe"])
    user_email: Optional[EmailStr]
    source: str = Field(examples=["Authentication"])
    action: str = Field(examples=["Login"])
    is_success: bool = Field(examples=[False])
    details: Optional[str] = Field(examples=["The password is incorrect"], default=None)
    created_at: datetime


class AuditLogsPaginator(BasePaginator):
    items: list[AuditLogPageSchema]
