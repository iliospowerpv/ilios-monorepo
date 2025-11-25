import enum
from typing import Any, List, Optional

import numpy as np
from pydantic import BaseModel

from src.deployment.cloud_run_job.key_value_extraction.response_status import Status


class ComparisonStatus(str, enum.Enum):
    EQUAL = "Equal"
    NOT_EQUAL = "Not Equal"
    AMBIGUOUS = "Ambiguous"
    NA = "N/A"

    @staticmethod
    def from_bool(value: bool | Any) -> "ComparisonStatus":
        """Value should in either bool or numpy NaN"""
        if value is True:
            return ComparisonStatus.EQUAL
        elif value is False:
            return ComparisonStatus.NOT_EQUAL
        elif value is np.nan:
            return ComparisonStatus.NA
        else:
            return ComparisonStatus.AMBIGUOUS


class CoterminousOutputItem(BaseModel):
    name: str
    status: ComparisonStatus


class CoterminousOutputPayload(BaseModel):
    status: Status
    items: List[CoterminousOutputItem]
    message: Optional[str] = None


class SimpleResponse(BaseModel):
    message: str
    status: int
