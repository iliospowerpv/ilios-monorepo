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


class FileParsingStatus(BaseModel):
    status: FileParsingStatuses | None = Field(default=FileParsingStatuses.not_started, examples=["Completed"])
    start_time: datetime | None = Field(default=None, examples=["2024-04-15T11:58:22.183013"])
    end_time: datetime | None = Field(default=None, examples=["2024-04-15T11:58:22.183013"])


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


class FileKeysList(BaseModel):
    keys: list[FileKeySchema]


class FileIsActual(BaseModel):
    is_actual: bool = Field(examples=["true"])


class FileUpdateIsActualSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["File is actual status has been updated successfully"])
