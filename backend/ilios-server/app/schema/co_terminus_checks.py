from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.file import FileParsingStatuses
from app.schema.common import SuccessUpdateSchema
from app.schema.file import FileParsingStatus
from app.static import CoTerminusMessages
from app.static.co_terminus_checks import CoTerminusComparisonStatuses


class CoTerminusStartSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=[CoTerminusMessages.check_start_success])


class CoTerminusCheckStatus(FileParsingStatus):
    # the response object is the same as for the FileParsingStatus, use it as a baseline
    is_actual: bool = Field(True, examples=[True])
    duration: Optional[int] = Field(None, examples=[42], description="Processing duration in seconds")
    is_stuck: bool = Field(False, examples=[False], description="Indicates if execution is longer than threshold")


class CoTerminusCheckResultItem(BaseModel):
    name: str = Field(examples=["Initial Term"])
    status: str = Field(examples=["Equal"])
    sources: dict


class CoTerminusCheckResultSummaryItem(BaseModel):
    status: str = Field(examples=["Equal"])
    count: int = Field(examples=[42])


class CoTerminusCheckResultsList(BaseModel):
    summary: Optional[List[CoTerminusCheckResultSummaryItem]]
    items: Optional[List[CoTerminusCheckResultItem]]


class CoTerminusResultSavingSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=[CoTerminusMessages.check_results_save_success])


class CoTerminusCheckResultUpdateSchema(BaseModel):
    name: str = Field(description="Term name", examples=["Effective Date"])
    status: CoTerminusComparisonStatuses = Field(examples=["Equal"])


class CoTerminusCheckResultUpdateRequestSchema(BaseModel):
    status: FileParsingStatuses = Field(examples=["Completed"])
    items: Optional[List[CoTerminusCheckResultUpdateSchema]]


class CoTerminusProcessAbortingSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=[CoTerminusMessages.check_is_aborted])
