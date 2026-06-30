"""Schemas for Data Room Templates (Task #91)."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schema.message import Success


class TemplateDocumentNode(BaseModel):
    kind: str = Field(examples=["site_lease"], description="Stable SiteDocumentsEnum member key")
    description: Optional[str] = Field(default=None, examples=["Executed lease for the project site land."])
    guidance: Optional[str] = Field(default=None, examples=["Upload the fully executed lease."])
    required: bool = Field(default=True, examples=[True])


class TemplateSubsectionNode(BaseModel):
    key: str = Field(examples=["site_stage1"], description="Stable DocumentSections member key")
    documents: list[TemplateDocumentNode] = Field(default_factory=list)


class TemplateSectionNode(BaseModel):
    key: str = Field(examples=["stage1"], description="Stable DocumentSections member key")
    documents: list[TemplateDocumentNode] = Field(default_factory=list)
    subsections: list[TemplateSubsectionNode] = Field(default_factory=list)


class TemplateStructureSchema(BaseModel):
    version: int = Field(default=1, examples=[1])
    sections: list[TemplateSectionNode] = Field(default_factory=list)


class TemplateSummarySchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Standard Solar DD Template"])
    description: Optional[str] = Field(default=None)
    is_archived: bool = Field(examples=[False])
    section_count: int = Field(examples=[6], description="Number of top-level sections")
    document_count: int = Field(examples=[120], description="Total expected documents across the template")
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)


class TemplateListSchema(BaseModel):
    items: list[TemplateSummarySchema]


class TemplateDetailSchema(TemplateSummarySchema):
    structure: TemplateStructureSchema


class CreateTemplateFromDataRoomSchema(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["Standard Solar DD Template"])
    description: Optional[str] = Field(default=None, max_length=2000)
    model_config = ConfigDict(extra="forbid")


class CreateTemplateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=200, examples=["Blank Template"])
    description: Optional[str] = Field(default=None, max_length=2000)
    structure: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional structure JSON. Defaults to the canonical Data Room blueprint when omitted.",
    )
    model_config = ConfigDict(extra="forbid")


class UpdateTemplateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    model_config = ConfigDict(extra="forbid")


class DuplicateTemplateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    model_config = ConfigDict(extra="forbid")


class ImportTemplateSchema(BaseModel):
    payload: dict[str, Any] = Field(description="Exported template envelope or a bare structure object")
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    model_config = ConfigDict(extra="forbid")


class TemplateExportSchema(BaseModel):
    format: str = Field(examples=["ilios.data_room_template"])
    export_version: int = Field(examples=[1])
    name: str = Field(examples=["Standard Solar DD Template"])
    description: Optional[str] = Field(default=None)
    structure: dict[str, Any]


class TemplateMutationSuccess(Success):
    id: int = Field(examples=[1])
    message: str = Field(examples=["Template has been created"])
