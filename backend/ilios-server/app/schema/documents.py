from datetime import date, datetime
from typing import Optional, Union

from pydantic import BaseModel, Field

from app.models.document import SiteDocumentsEnum
from app.models.task import TaskPriorityEnum
from app.schema.common import SuccessUpdateSchema
from app.schema.message import Success
from app.schema.site import SitesSettingsSchema
from app.schema.task import TaskUser
from app.static import DocumentMessages


class BaseDocumentSchema(BaseModel):
    id: int = Field(examples=[1])
    name: SiteDocumentsEnum = Field(examples=["O&M Agreement"])


class DocumentSection(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["O&M Agreement"])


class DocumentUserSchema(BaseModel):
    id: int = Field(examples=[1])
    first_name: str = Field(examples=["Will"])
    last_name: str = Field(examples=["Smith"])


class DocumentTaskStatusSchema(BaseModel):
    id: int = Field(examples=["1"])
    name: str = Field(examples=["To Do"])


class DocumentTaskSchema(BaseModel):
    id: int = Field(examples=[14])
    board_id: int = Field(examples=[15])
    name: str = Field(examples=["Default task for document #14"])
    priority: TaskPriorityEnum
    due_date: Optional[date] = Field(default=None)
    assignee: Optional[DocumentUserSchema]
    status: DocumentTaskStatusSchema


class DocumentDetailsSchema(BaseDocumentSchema):
    # type - is a new field, which appears only on the individual document getting and is hardcoded in the MVP
    type: Optional[str] = Field(examples=["Diligence"], default="Diligence")
    site: SitesSettingsSchema
    section: DocumentSection
    description: Union[str, None] = Field(examples=["This is due diligence requirement description"], default=None)
    approver: Optional[DocumentUserSchema]
    task: DocumentTaskSchema
    display_working_zone: bool = Field(examples=[False])


class SiteDocumentDetailsSchema(BaseDocumentSchema):
    files_count: int = Field(default=0, examples=[0])
    status: str = Field(examples=["To Upload"])
    assignee: Optional[TaskUser]
    ai_supported: bool = Field(examples=[False])


class SiteDocumentsSchema(BaseModel):
    documents: list[SiteDocumentDetailsSchema]


class DocumentSectionSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["This is due diligence section name"])
    documents_count: int = Field(examples=[1])
    completed_tasks_percentage: int = Field(examples=[30])
    documents: list[SiteDocumentDetailsSchema]


class UpdateDocumentDescriptionSchema(BaseModel):
    description: Union[str, None] = Field(examples=["Updated description"], default=None, max_length=200)


class UpdateDocumentDetailsSchema(BaseModel):
    approver_id: Optional[int] = Field(None, examples=[42])


class DocumentUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=[DocumentMessages.document_update_success])


class DocumentCreationSuccess(Success):
    message: str = Field(description="Success message", examples=[DocumentMessages.document_create_success])


class DocumentRemovalSuccess(Success):
    message: str = Field(description="Success message", examples=[DocumentMessages.document_remove_success])


class DocumentCreationSchema(BaseModel):
    section_id: int = Field(examples=[1])
    name: SiteDocumentsEnum = Field(examples=["O&M Agreement"])
    description: Union[str, None] = Field(examples=["This is due diligence requirement description"], default=None)


class DocumentKeyUpdateSchema(BaseModel):
    name: str = Field(examples=["Lessor (Landlord) Entity Name"])
    value: str = Field(examples=["GreenLife Solar, LLC Shine Development Partners"], min_length=1, max_length=2000)


class DocumentKeyUpdateSuccess(Success):
    id: int = Field(examples=[1], description="ID of updated/created document key object")
    message: str = Field(description="Success message", examples=["Document key has been successfully updated"])


class ParsableDocumentSchema(BaseModel):
    id: int = Field(examples=[1])
    name: str = Field(examples=["Site lease"])


class ParsableDocumentsListSchema(BaseModel):
    items: list[ParsableDocumentSchema]


class DocumentKeySchema(BaseModel):
    name: str = Field(examples=["Lessor (Landlord) Entity Name"])
    value: Optional[str] = Field(None, examples=["GreenLife Solar, LLC Shine Development Partners"])
    updated_at: Optional[datetime] = Field(None)


class DocumentKeysListSchema(BaseModel):
    items: list[DocumentKeySchema]


class SiteIDSchema(BaseModel):
    site_ids: Optional[list] = Field([], examples=[1, 2, 3])
