import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.helpers.files.common import validate_file_extension
from app.models.file import FileParsingStatuses
from app.schema.comment import CommentsPageSchema
from app.schema.common import SuccessUpdateSchema
from app.settings import settings
from app.static import FileMessages


class FileUploadSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["File successfully uploaded"])
    id: Optional[int] = Field(
        default=None, description="ID of the newly created file record", examples=[1]
    )


class FileSchema(BaseModel):
    id: int = Field(examples=[1])
    author: str = Field(examples=["John Doe"])
    filename: str = Field(examples=["analytics.pdf"])
    extension: Optional[str] = Field(None, examples=["pdf"], validate_default=True)
    created_at: datetime = Field(examples=["2024-04-15T11:58:22.183013"])
    is_actual: bool = Field(examples=[True])

    @field_validator("extension")
    @classmethod
    def get_file_type(cls, extension, info):  # noqa: U100
        return info.data.get("filename").split(".")[-1]


class FilesList(BaseModel):
    items: list[FileSchema]


class FileRemovalSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["File has been successfully deleted"])


class FileRemovalSchema(BaseModel):
    note: str = Field(
        min_length=1,
        description="Required reason/note explaining why this file version is being deleted.",
        examples=["Uploaded the wrong revision of the lease."],
    )

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, note):
        stripped = note.strip()
        if not stripped:
            raise ValueError("A non-empty reason is required.")
        return stripped


class FileDownloadURLSchema(BaseModel):
    download_url: HttpUrl = Field(examples=["http://example.com"])


class FilePreviewURLSchema(BaseModel):
    preview_url: HttpUrl = Field(examples=["http://example.com"])


class FileUploadURLSchema(BaseModel):
    filepath: str = Field(examples=["/companies/1/sites/1/documents/1/file.pdf"])
    upload_url: HttpUrl = Field(examples=["http://example.com"])


class FileNameSchema(BaseModel):
    filename: str = Field(examples=["analytics.pdf"])

    @field_validator("filename")
    @classmethod
    def file_extension_validation(cls, filename):
        return validate_file_extension(filename, settings.allowed_extensions)


class ImageFileNameSchema(BaseModel):
    filename: str = Field(examples=["analytics.png"])

    @field_validator("filename")
    @classmethod
    def file_extension_validation(cls, filename):
        return validate_file_extension(filename, settings.sa_uploads_allowed_extensions)


class CreateImageFileSchema(ImageFileNameSchema):
    filepath: str = Field(examples=["path/to/image.png"])


class CreateFileSchema(FileNameSchema):
    filepath: str = Field(examples=["companies/1/sites/1/documents/1/2024-2-5T11:00:12_file.pdf"])


class ProcessedFileResult(BaseModel):
    status: FileParsingStatuses = Field(examples=["Completed"])
    result: Optional[list[dict]] = Field(default=[{"term": "result"}], alias="result")
    ai_model_version: str = Field(examples=["claude3-sonnet"])
    ai_app_version: str = Field(examples=["0.0.29"])


class FileUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["File parsing results has been stored"])


class FileParseTriggerSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=[FileMessages.file_parse_trigger_success])
    run_id: int = Field(description="The parsing run ID (AIParsingResult.id)", examples=[42])
    correlation_id: str = Field(description="Unique correlation ID for tracing", examples=["abc12345"])
    status: str = Field(description="Current status of the parsing job", examples=["queued"])


class FileParsingStatus(BaseModel):
    status: FileParsingStatuses | None = Field(default=FileParsingStatuses.not_started, examples=["Completed"])
    start_time: datetime | None = Field(default=None, examples=["2024-04-15T11:58:22.183013"])
    end_time: datetime | None = Field(default=None, examples=["2024-04-15T11:58:22.183013"])


class FileParsingEvidence(BaseModel):
    page: Optional[int] = Field(None, examples=[1], description="Page number in the PDF where evidence was found")
    snippet: Optional[str] = Field(None, examples=["The lease agreement dated..."], description="Text snippet from the document")
    anchor_text: Optional[str] = Field(None, examples=["lease agreement"], description="Specific anchor text to highlight")
    # Additive (DD V2 Phase 2): the datasheet table/section the value was read from
    # (e.g. "Electrical Data (STC)"). Optional; older evidence payloads omit it.
    table_or_section: Optional[str] = Field(
        None, examples=["Electrical Data (STC)"], description="Table or section name the value was read from"
    )


class FileKeySchema(BaseModel):
    id: Optional[int] = Field(None, examples=[1], description="Might be empty if key doesn't exist in the DB")
    name: str = Field(examples=["Lessor (Landlord) Entity Name"])
    value: Optional[str] = Field(None, examples=["GreenLife Solar, LLC Shine Development Partners"])
    ai_value: Optional[str] = Field(None, examples=["Agreement between Jared N. Connell and Nutting Ridge Solar LLC."])
    is_poison_pill: bool = Field(False, examples=[False])
    poison_pill: Optional[str] = Field(None, examples=["Yes, the rule is violated."])
    poison_pill_detailed: Optional[str] = Field(None, examples=["The statement presents contradictory information."])
    updated_at: Optional[datetime] = Field(None)
    legal_term: Optional[str] = Field(None, examples=["Commercial Operation Date"])
    comments: Optional[list[CommentsPageSchema]] = Field(None)
    evidence: Optional[FileParsingEvidence] = Field(None, description="Source evidence from the parsed document")
    is_baseline_driving: bool = Field(
        False,
        description=(
            "True if this field feeds the energy-production baseline; overriding it requires a "
            "documented rationale (DD V2 Phase 1D)."
        ),
    )
    # --- DD V2 Phase 2: additive equipment-extraction metadata (all optional) ---
    # These surface the richer parse output (raw value + printed unit, confidence,
    # extraction status, and per-variant data) for equipment datasheets. They are
    # purely additive and default to None, so contractual document types and older
    # parse results are unaffected. None of these ever trigger a unit conversion or
    # auto-select a value for an ambiguous field.
    raw_value: Optional[str] = Field(
        None, examples=["405"], description="The AI-extracted value exactly as printed, without the unit."
    )
    raw_unit: Optional[str] = Field(
        None, examples=["W"], description="The unit exactly as printed in the document (never converted)."
    )
    expected_unit: Optional[str] = Field(
        None, examples=["W"], description="The canonical/expected unit for this field (display hint only)."
    )
    confidence: Optional[str] = Field(
        None, examples=["high"], description="AI-reported extraction confidence: high | medium | low."
    )
    extraction_status: Optional[str] = Field(
        None,
        examples=["ambiguous"],
        description="AI-reported per-field status: extracted | ambiguous | unclear | not_found.",
    )
    variants: Optional[list[dict]] = Field(
        None,
        description=(
            "When a datasheet field differs across module variants/SKUs (e.g. multiple power "
            "classes), every variant is listed here verbatim. The reviewer must choose; the system "
            "never auto-selects one and creates no candidate fact for an ambiguous field."
        ),
    )


class FileKeysList(BaseModel):
    keys: list[FileKeySchema]


class FileIsActual(BaseModel):
    is_actual: bool = Field(examples=["true"])


class FileUpdateIsActualSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["File is actual status has been updated successfully"])


# ---------------------------------------------------------------------------
# Data Room Parse-State Visibility (Phase 1) — additive, read-only summary.
#
# These schemas back the GET .../files/{file_id}/parse-state/ endpoint, which
# provides an honest, single summary of where a file version sits in the
# parse → review → accept/override → promote lifecycle. They DO NOT replace the
# existing detailed FileParsingStatuses; they only add a higher-level summary so
# the UI can stop rendering silently-empty documents. Computing this summary
# performs zero writes and never mutates parsed/accepted values or facts.
# ---------------------------------------------------------------------------


class ParseState(str, enum.Enum):
    """Most-advanced-stage-wins summary of a file version's parse lifecycle."""

    not_yet_parsed = "not_yet_parsed"
    parsing_in_progress = "parsing_in_progress"
    parse_failed = "parse_failed"
    parsed_no_usable_fields = "parsed_no_usable_fields"
    parsed_awaiting_review = "parsed_awaiting_review"
    accepted_or_overridden = "accepted_or_overridden"
    promoted = "promoted"


class NoUsableFieldsReason(str, enum.Enum):
    """Why a completed parse produced nothing reviewable (set only for
    parse_state == parsed_no_usable_fields)."""

    no_schema_fields = "no_schema_fields"
    no_fields_found = "no_fields_found"
    fields_did_not_map = "fields_did_not_map"
    generic_contractual_schema = "generic_contractual_schema"


class ParseNextAction(str, enum.Enum):
    """A hint for the single most useful next user action. The frontend renders
    the actual control/copy; this only conveys intent."""

    parse_document = "parse_document"
    wait_for_parse = "wait_for_parse"
    retry_parse = "retry_parse"
    review_fields = "review_fields"
    review_or_promote = "review_or_promote"
    change_document_type = "change_document_type"
    awaiting_equipment_schema = "awaiting_equipment_schema"
    none = "none"


class SelectedDocumentTypeSchema(BaseModel):
    key: Optional[str] = Field(None, description="SiteDocumentsEnum member name", examples=["module_specs"])
    display: Optional[str] = Field(None, description="Human-readable document type", examples=["Module Specs"])
    is_generic_contractual_stub: bool = Field(
        False,
        description="True if this type's active schema is the shared generic contractual 10-field stub (no specialized fields).",
    )
    is_equipment_type: bool = Field(
        False,
        description="True if this is an equipment datasheet type (module/inverter/transformer/storage/battery/racking specs).",
    )


class ParseStateFileVersionSchema(BaseModel):
    id: int = Field(examples=[25])
    is_current_version: bool = Field(examples=[False])
    is_sole_version: bool = Field(
        False, description="True if this is the only non-deleted version of its document."
    )
    version_display: str = Field(examples=["Version 25"])


class ParseStateLatestRunSchema(BaseModel):
    id: int = Field(examples=[42])
    status: str = Field(examples=["Completed"])
    extraction_run_number: Optional[int] = Field(None, examples=[1])
    created_at: Optional[datetime] = Field(None)
    start_time: Optional[datetime] = Field(None)
    end_time: Optional[datetime] = Field(None)


class ParseStateSummary(BaseModel):
    file_id: int = Field(examples=[25])
    parse_state: ParseState = Field(examples=[ParseState.not_yet_parsed])
    selected_document_type: SelectedDocumentTypeSchema
    file_version: ParseStateFileVersionSchema
    last_parse_attempt_at: Optional[datetime] = Field(
        None, description="Timestamp of the most recent parse run attempt, if any."
    )
    latest_run: Optional[ParseStateLatestRunSchema] = Field(None)
    reviewable_field_count: int = Field(
        0, description="Count of latest-completed-run fields that map to the active schema and carry a value."
    )
    accepted_overridden_count: int = Field(
        0, description="Count of this version's accepted/overridden document keys."
    )
    promoted_count: int = Field(
        0, description="Count of active project facts promoted from this file version."
    )
    no_usable_fields_reason: Optional[NoUsableFieldsReason] = Field(None)
    next_action: ParseNextAction = Field(examples=[ParseNextAction.parse_document])
    active_reprocess_in_progress: bool = Field(
        False,
        description="True when durable data exists but a newer parse run is queued/processing; the durable state is preserved (not regressed).",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Stable warning codes (e.g. not_current_version, sole_non_current_version, no_equipment_extraction_schema) the UI maps to copy.",
    )
