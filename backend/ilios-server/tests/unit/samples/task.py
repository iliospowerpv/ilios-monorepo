from copy import deepcopy
from datetime import date, timedelta

from app.models.task import TaskPriorityEnum

TEST_TEXT_2001_SYMBOLS_LEN = "i" * 2001
TEST_TEXT_101_SYMBOLS_LEN = "i" * 101
TEST_TASK_BODY = {"name": "Test task", "priority": TaskPriorityEnum.medium, "due_date": "2030-10-20"}
TEST_TASK_PAYLOAD = {
    "name": "Fixture task",
    "external_id": "TST-1",
    "due_date": "2030-10-20",
    "priority": TaskPriorityEnum.medium.value,
}

TEST_TASK_EXPECTED_LIST_PAYLOAD = deepcopy(TEST_TASK_PAYLOAD)
TEST_TASK_EXPECTED_LIST_PAYLOAD.update(
    {
        "description": None,
        "affected_device": None,
        "summary_of_events": None,
        "site_visit_added": False,
    }
)

TEST_SITE_VISIT_PAYLOAD = {
    "service_date": "2025-02-11",
    "technician_assignee": "Joe Fr. Doe",
    "reasons": "Annual devices check",
    "scope_of_work": "Ensure all devices are connected properly",
    "status": "Resolved",
    "resolution": "Yearly maintenance goes smoothly",
    "next_steps": "Update device #3 in 2 months",
    "pending_work": "Device #3 replacement on 2025-04-11",
    "recommendations": "Follow the suggested maintenance schedule",
}

TEST_SITE_VISIT_PAYLOAD_INVALID = {
    "service_date": "not a date",
    "technician_assignee": TEST_TEXT_101_SYMBOLS_LEN,
    "reasons": TEST_TEXT_2001_SYMBOLS_LEN,
    "scope_of_work": TEST_TEXT_2001_SYMBOLS_LEN,
    "status": "Invalid Status",
    "resolution": TEST_TEXT_2001_SYMBOLS_LEN,
    "next_steps": TEST_TEXT_2001_SYMBOLS_LEN,
    "pending_work": TEST_TEXT_2001_SYMBOLS_LEN,
    "recommendations": TEST_TEXT_2001_SYMBOLS_LEN,
}

MISSING_TASK_BODY_MSG = (
    "Validation error: body.name - Field required; body.priority - Field required; body.due_date - Field required; "
    "body.status_id - Field required"
)
INVALID_TASK_STATUS_MSG = "Invalid status ID"
INVALID_TASK_ASSIGNEE_MSG = "Invalid assignee ID"
INVALID_TASK_AFFECTED_DEVICE_MSG = "Invalid affected device ID"
INVALID_TASK_DUE_DATE_NOT_DATE_MSG = (
    "Validation error: body.due_date - Input should be a valid date or datetime, input is too short"
)
INVALID_TASK_DUE_DATE_FORMATTING_MSG = (
    "Validation error: body.due_date - Input should be a valid date or datetime, "
    "month value is outside expected range of 1-12"
)
INVALID_TASK_DUE_DATE_IN_PAST_MSG = "Invalid Due Date: value must be a date of today or date in future"
INVALID_TASK_PRIORITY_MSG = "Validation error: body.priority - Input should be 'Low', 'Medium' or 'High'"

COMMON_TASK_PAYLOAD_FOR_CUSTOM_ERRORS_DATA = (
    # Custom errors
    # Status ID from request doesn't belong to the dashboard
    ({"status_id": 99999}, 400, INVALID_TASK_STATUS_MSG),
    # Assignee doesn't have access to the board
    ({"assignee_id": 99999}, 400, INVALID_TASK_ASSIGNEE_MSG),
    # default errors
    # Invalid due date format
    ({"due_date": "wrong"}, 422, INVALID_TASK_DUE_DATE_NOT_DATE_MSG),
    # Invalid due date data
    ({"due_date": "9999-99-99"}, 422, INVALID_TASK_DUE_DATE_FORMATTING_MSG),
    # Invalid priority
    ({"priority": "something new"}, 422, INVALID_TASK_PRIORITY_MSG),
)

TASK_CREATION_PAYLOAD_FOR_CUSTOM_ERRORS_DATA = (
    *COMMON_TASK_PAYLOAD_FOR_CUSTOM_ERRORS_DATA,
    # Due date in past
    ({"due_date": "2022-12-12"}, 400, INVALID_TASK_DUE_DATE_IN_PAST_MSG),
)

TASK_UPDATE_PAYLOAD_FOR_CUSTOM_ERRORS_DATA = COMMON_TASK_PAYLOAD_FOR_CUSTOM_ERRORS_DATA

TASK_DESCRIPTION_TOO_LONG_ERR = "Validation error: body.description - String should have at most 2000 characters"
TASK_SUMMARY_OF_EVENTS_TOO_LONG_ERR = (
    "Validation error: body.summary_of_events - String should have at most 2000 characters"
)
SITE_VISIT_VALIDATION_ERROR = (
    "Validation error: body.service_date - Input should be a valid date or datetime, invalid character in year; "
    "body.technician_assignee - String should have at most 100 characters; body.reasons - String should have at most "
    "2000 characters; body.scope_of_work - String should have at most 2000 characters; body.status - Input should be "
    "'Resolved', 'Escalated' or 'RMA'; body.resolution - String should have at most 2000 characters; body.next_steps "
    "- String should have at most 2000 characters; body.pending_work - String should have at most 2000 characters; "
    "body.recommendations - String should have at most 2000 characters"
)


def make_task_details_payload(board, assignee_id):
    task_details = {
        "name": "New task details",
        "priority": TaskPriorityEnum.low,
        "due_date": str(date.today() + timedelta(days=1)),  # make sure date is always in future
        "assignee_id": assignee_id,
        "status_id": board.get_statuses_ids()[0],
    }
    return task_details
