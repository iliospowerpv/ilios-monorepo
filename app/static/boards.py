from enum import Enum


class DefaultStatusBase(Enum):

    @classmethod
    def list(cls):
        return [option.value for option in list(cls)]


class SiteBoardDefaultStatuses(DefaultStatusBase):
    new = "New"
    assigned = "Assigned"
    in_process = "In Process"
    escalated = "Escalated"
    completed = "Completed"
    closed = "Closed"
    cancelled = "Cancelled"


class CompanyBoardDefaultStatuses(DefaultStatusBase):
    new = "New"
    assigned = "Assigned"
    in_process = "In Process"
    escalated = "Escalated"
    completed = "Completed"
    closed = "Closed"
    cancelled = "Cancelled"


class DocumentBoardDefaultStatuses(DefaultStatusBase):
    to_upload = "To Upload"
    under_review = "Under Review"
    addressing_issues = "Addressing Issues"
    completed = "Completed"
    rejected = "Rejected"


DEFAULT_BOARD_PREFIX = "TG"
