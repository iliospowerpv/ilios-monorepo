from pydantic import BaseModel, Field

from app.schema.message import Success


class BaseStatusSchema(BaseModel):
    name: str = Field(examples=["TO DO"])


class StatusItemSchema(BaseStatusSchema):
    id: int = Field(examples=[1])
    name: str = Field(examples=["TO DO"])


class StatusListSchema(BaseModel):
    items: list[StatusItemSchema]


class StatusCreationSuccess(Success):
    message: str = Field(description="Success message", examples=["Status has been successfully added"])


class StatusNameUpdateSuccess(Success):
    message: str = Field(description="Success message", examples=["Status name has been successfully updated"])


class StatusRemovalSuccess(Success):
    message: str = Field(description="Success message", examples=["Status has been successfully deleted"])
