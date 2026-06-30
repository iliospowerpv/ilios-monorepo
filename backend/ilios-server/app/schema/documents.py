from datetime import date, datetime
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator

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


class DocumentIdentitySchema(BaseModel):
    """Formalized logical Document Identity (Task #90).

    The existing ``Document`` row is the canonical identity; this is the additive,
    resolved view of its identity metadata used for display and later matching.
    """

    document_id: int = Field(examples=[1])
    kind: Optional[str] = Field(default=None, examples=["site_lease"], description="Stable document-type enum key")
    canonical_name: Optional[str] = Field(default=None, examples=["Site Lease"])
    aliases: list[str] = Field(default_factory=list, examples=[["Ground Lease", "Lease Agreement"]])


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
    identity: Optional[DocumentIdentitySchema] = Field(default=None)


class SiteDocumentDetailsSchema(BaseDocumentSchema):
    files_count: int = Field(default=0, examples=[0])
    status: str = Field(examples=["To Upload"])
    assignee: Optional[TaskUser]
    ai_supported: bool = Field(examples=[False])
    custom_name: Optional[str] = Field(default=None, examples=["Custom Document Name"])
    display_name: Optional[str] = Field(default=None, examples=["Custom Document Name"])
    identity: Optional[DocumentIdentitySchema] = Field(default=None)


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
    file_id: Optional[int] = Field(default=None, examples=[123], description="File version ID for version-scoped keys")
    status: Optional[str] = Field(default="accepted", examples=["accepted", "overridden", "proposed"])
    override_value: Optional[str] = Field(default=None, max_length=2000)
    override_notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Reviewer rationale. Required when overriding a baseline-driving field (DD V2 Phase 1D).",
    )


class DocumentKeyUpdateSuccess(Success):
    id: int = Field(examples=[1], description="ID of updated/created document key object")
    message: str = Field(description="Success message", examples=["Document key has been successfully updated"])


class DocumentKeyPoisonPillSchema(BaseModel):
    is_poison_pill: bool = Field(examples=[True])
    poison_pill_notes: Optional[str] = Field(default=None, max_length=2000)
    key_name: Optional[str] = Field(default=None, max_length=500, description="Key name for upsert when key_id is 0")
    file_id: Optional[int] = Field(default=None)


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


class DocumentReorderSchema(BaseModel):
    position: int = Field(ge=1, examples=[1], description="New position for the document (1-indexed)")


class DocumentArchiveSuccess(Success):
    message: str = Field(description="Success message", examples=["Document has been archived"])


class DocumentArchiveSchema(BaseModel):
    note: str = Field(
        min_length=1,
        description="Required reason/note explaining why this document is being archived.",
        examples=["Superseded by the executed version."],
    )

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, note):
        stripped = note.strip()
        if not stripped:
            raise ValueError("A non-empty reason is required.")
        return stripped


class CustomDocumentCreationSchema(BaseModel):
    section_id: int = Field(examples=[1])
    custom_name: str = Field(min_length=1, max_length=200, examples=["Custom Document Name"])
    description: Union[str, None] = Field(examples=["This is a custom document description"], default=None)


class ExpectedDocumentSchema(BaseModel):
    """A single expected document definition for a stage/section (Task #90).

    Declarative only — never materializes a Document/File row.
    """

    kind: str = Field(examples=["site_lease"], description="Stable document-type enum key")
    name: str = Field(examples=["Site Lease"], description="Human-readable document name")
    description: Optional[str] = Field(default=None, examples=["Executed lease for the project site land."])
    required: bool = Field(examples=[True])
    position: int = Field(examples=[1], description="1-indexed ordering within the section")


class ExpectedDocumentsSectionSchema(BaseModel):
    """Expected documents grouped under one section of a site's Data Room."""

    section_id: Optional[int] = Field(default=None, examples=[1], description="Site section row id when present")
    section_key: str = Field(examples=["site_stage1"], description="Stable section enum key")
    section_name: str = Field(examples=["Site Stage-1"])
    expected_documents: list[ExpectedDocumentSchema]


class SiteExpectedDocumentsSchema(BaseModel):
    items: list[ExpectedDocumentsSectionSchema]


class DuplicateMatchSchema(BaseModel):
    """An existing Document Identity that resembles a proposed name (Task #92).

    Advisory only — surfaced so the user can choose to upload a new version to the
    existing identity instead of accidentally creating a second one.
    """

    document_id: int = Field(examples=[101])
    name: str = Field(examples=["PVsyst Final"], description="Resolved identity/display name")
    kind: Optional[str] = Field(default=None, examples=["seller_initial_pv_syst_full_data_package_for_model"])
    section_id: Optional[int] = Field(default=None, examples=[5])
    section_name: Optional[str] = Field(default=None, examples=["Preview"])
    files_count: int = Field(examples=[2], description="Uploaded file versions on the existing identity")
    is_archived: bool = Field(examples=[False])
    match_type: str = Field(examples=["near"], description='"exact" or "near"')
    score: float = Field(examples=[0.92], description="0..1 similarity, higher is closer")


class DuplicateCheckResultSchema(BaseModel):
    """Read-only result of checking a proposed document name against a site."""

    proposed_name: str = Field(examples=["PVsyst"])
    has_match: bool = Field(examples=[True])
    candidates: list[DuplicateMatchSchema]


class GuidanceStageSchema(BaseModel):
    """Per-stage completeness/guidance row for the Data Room dashboard (Task #92)."""

    section_id: Optional[int] = Field(default=None, examples=[1])
    section_key: str = Field(examples=["site_stage1"])
    section_name: str = Field(examples=["Site Stage-1"])
    expected: int = Field(examples=[8], description="Expected documents from the static catalog")
    present: int = Field(examples=[5], description="Expected documents with a live, file-bearing identity")
    missing: int = Field(examples=[3])
    needs_update: int = Field(examples=[1], description="Promoted documents that received a newer version since")
    optional: int = Field(examples=[2], description="Expected documents flagged optional")
    archived: int = Field(examples=[1], description="Archived documents in the stage")
    version_count: int = Field(examples=[9], description="Total file versions across live documents")
    promotion_status: str = Field(examples=["in_progress"], description="none|not_started|in_progress|complete")
    missing_documents: list[ExpectedDocumentSchema]


class SiteDataRoomGuidanceSchema(BaseModel):
    items: list[GuidanceStageSchema]
