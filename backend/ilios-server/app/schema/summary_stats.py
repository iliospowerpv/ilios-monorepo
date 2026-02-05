from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CoTerminusStats(BaseModel):
    status: Optional[str] = Field(
        None,
        description="Co-terminus check status: not_run, running, completed, stuck, failed, or null"
    )
    mismatches: Optional[int] = Field(
        None,
        description="Number of mismatches from the latest completed run"
    )
    last_run_at: Optional[datetime] = Field(
        None,
        description="Timestamp of the last completed run"
    )


class ProjectSummaryStats(BaseModel):
    documents_total: int = Field(
        description="Total number of due diligence document slots for the site"
    )
    documents_with_promoted_terms: int = Field(
        description="Count of distinct documents that have promoted (active) terms"
    )
    promoted_terms_total: int = Field(
        description="Total count of promoted (active) fact rows with meaningful values"
    )
    coterminus: CoTerminusStats = Field(
        description="Co-terminus check status and summary"
    )
