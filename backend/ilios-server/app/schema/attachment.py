from typing import ClassVar

from pydantic import BaseModel, Field

from app.schema.file import FileNameSchema, FileSchema


class CreateAttachmentSchema(FileNameSchema):
    filepath: str = Field(examples=["boards/1/tasks/1/2024-12-5T11:00:12_analytics.pdf"])


class AttachmentSchema(FileSchema):
    is_actual: ClassVar[str]


class AttachmentsList(BaseModel):
    items: list[AttachmentSchema]
