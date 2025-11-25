from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.device_document import DocumentCategories
from app.schema.file import CreateFileSchema


class CreateDocumentSchema(CreateFileSchema):
    category: DocumentCategories = Field(examples=["Warranty"])


class DocumentSchema(BaseModel):
    id: int = Field(examples=[1])
    filename: str = Field(examples=["analytics.pdf"])
    author: str = Field(examples=["Jon Dou"])
    extension: Optional[str] = Field(None, examples=["pdf"], validate_default=True)
    created_at: datetime = Field(examples=["2024-04-15T11:58:22.183013"])

    @field_validator("extension")
    @classmethod
    def get_file_type(cls, extension, info):  # noqa: U100
        return info.data.get("filename").split(".")[-1]


class DocumentCategorySchema(BaseModel):
    category: DocumentCategories = Field(examples=["Warranty"])
    items: list[DocumentSchema]
