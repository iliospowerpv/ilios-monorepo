from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, SerializeAsAny, field_validator

from app.models.notification import NotificationKindsEnum
from app.schema.message import Success
from app.schema.paginator import BasePaginator
from app.static import NotificationMessages


class NotificationTaskSchema(BaseModel):
    id: int = Field(examples=[1])
    external_id: str = Field(examples=["IOSP1-894"])
    module: str = Field(examples=["Asset"])


class NotificationRelatedObjectSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Duplex"])


class NotificationTaskStatusSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Duplex"])


class NotificationUserSchema(BaseModel):
    id: int = Field(examples=[1])
    first_name: str = Field(examples=["Jane"])
    last_name: str = Field(examples=["Doe"])


class NotificationCommentSchema(BaseModel):
    text: str = Field(examples=["FYI: @LeadUser take a look?"])
    entity_id: int = Field(examples=[2])
    entity_type: str = Field(examples=["document"])


class NotificationSchema(BaseModel):

    id: int = Field(examples=[42])
    seen: bool = Field(examples=[False])
    kind: NotificationKindsEnum
    created_at: datetime
    task: Optional[NotificationTaskSchema] = Field(default=None)
    comment: Optional[NotificationCommentSchema] = Field(default=None)
    site: Optional[NotificationRelatedObjectSchema] = Field(default=None)
    company: NotificationRelatedObjectSchema
    actor: Optional[SerializeAsAny[NotificationUserSchema]] = Field(None)
    # allow extra to be any dict-like object
    extra: Any

    @field_validator("kind")
    @classmethod
    def serialize_kind(cls, template: NotificationKindsEnum, info):  # noqa: U100
        return template.name

    @field_validator("actor")
    @classmethod
    def set_actor(cls, actor):
        return actor or {"id": None, "first_name": "Deleted", "last_name": "User"}


class NotificationsListSchema(BasePaginator):
    unread_count: int
    items: list[NotificationSchema]


class NotificationUpdateSuccessSchema(Success):
    message: str = Field(description="Success message", examples=[NotificationMessages.mark_as_read_success])


class NotificationDeleteSuccessSchema(Success):
    message: str = Field(description="Success message", examples=[NotificationMessages.delete_success])
