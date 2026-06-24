from datetime import date, datetime
from enum import Enum
from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.board import BoardModuleEnum
from app.models.task import TaskPriorityEnum
from app.schema.message import Success
from app.schema.paginator import BasePaginator
from app.static import TEXT_AREA_MAX_LENGTH, TaskMessages


class TaskBaseSchema(BaseModel):
    name: str = Field(examples=["Review inverter #12 performance"])
    priority: TaskPriorityEnum
    due_date: Optional[date] = Field(default=None)


class TaskCreationPayloadSchema(TaskBaseSchema):
    assignee_id: Optional[int] = Field(examples=[1], default=None)
    status_id: int = Field(examples=[1])
    due_date: date = Field(examples=["2024-07-26"])
    affected_device_id: Optional[int] = Field(default=None, examples=[12])
    alert_id: Optional[int] = Field(default=None, examples=[12])
    description: Optional[str] = Field(examples=["Please, investigate and document inverter #12 metrics"], default=None)


class TaskCreationSuccess(Success):
    message: str = Field(description="Success message", examples=["Task has been successfully created"])
    entity_id: int = Field(description="Created task ID", examples=[1])


class InventoryMismatchTaskCreateSchema(BaseModel):
    """Explicit request to turn one actionable inventory-reconciliation mismatch
    into a tracked task. The board, default status, and device provenance are all
    resolved server-side from the (re-run, read-only) reconciliation; the client
    only supplies the human-editable task fields."""

    mismatch_signature: str = Field(
        examples=["undocumented_telemetry_device:inverter:abc123"],
        description="Stable signature of the mismatch to track (from the reconciliation payload).",
    )
    name: Optional[str] = Field(
        default=None,
        max_length=250,
        examples=["Inventory: map discovered inverter INV-04"],
        description="Task name. Defaults to a mismatch-derived title when omitted.",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=TEXT_AREA_MAX_LENGTH,
        examples=["Discovered an inverter in telemetry with no documented match..."],
        description="Task description. Defaults to a provenance-rich summary when omitted.",
    )
    priority: Optional[TaskPriorityEnum] = Field(
        default=None,
        description="Task priority. Defaults to a blocking-level-derived priority when omitted.",
    )
    due_date: Optional[date] = Field(default=None, examples=["2026-07-01"])
    assignee_id: Optional[int] = Field(default=None, examples=[1])


class InventoryMismatchTaskResponseSchema(BaseModel):
    """Outcome of an inventory-mismatch task create. ``created`` is False (and
    ``duplicate`` True) when an open task already tracks the same gap."""

    created: bool = Field(examples=[True], description="True if a new task was created, False if an open one existed.")
    duplicate: bool = Field(
        examples=[False], description="True when an open task already tracked this mismatch (no new task created)."
    )
    task_id: int = Field(examples=[42])
    external_id: Optional[str] = Field(default=None, examples=["IOSP1-894"])
    board_id: int = Field(examples=[7])
    mismatch_signature: str = Field(examples=["undocumented_telemetry_device:inverter:abc123"])
    message: str = Field(examples=["Task has been successfully created"])
    deep_link: str = Field(
        examples=["/project-hub/companies/3/sites/4/tasks/42"],
        description="Relative deep link to the created/existing task.",
    )


class TaskOrderByFieldEnum(str, Enum):
    id = "id"
    external_id = "external_id"
    name = "name"
    due_date = "due_date"


class TaskUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=["1"])
    first_name: str = Field(examples=["John"])
    last_name: str = Field(examples=["Doe"])


class TaskStatus(BaseModel):
    id: int = Field(examples=["1"])
    name: str = Field(examples=["To Do"])


class TaskAffectedDevice(BaseModel):
    id: int = Field(examples=["1"])
    name: str = Field(examples=["Base Inverter"])


class TaskListViewSchema(TaskBaseSchema):
    id: int = Field(examples=["1"])
    external_id: str = Field(examples=["IOSP1-894"])

    creator: TaskUser
    assignee: Optional[TaskUser]
    status: TaskStatus


class TasksListResponse(BasePaginator):

    items: list[TaskListViewSchema]


class TaskDetailsViewSchema(TaskListViewSchema):
    """Task list schema extended with specific fields"""

    # common for all types of tasks
    description: Optional[str] = Field(examples=["Please, investigate and document inverter #12 metrics"], default=None)

    # for the site level tasks, indicated if it's linked to the device
    affected_device: Optional[TaskAffectedDevice] = Field(default=None)

    # for the O&M tasks, represents if task is linked to the alert
    alert_id: Optional[int] = Field(default=None, examples=[42])

    # for Asset and O&M tasks
    summary_of_events: Optional[str] = Field(examples=["The team of 2 field engineers were assigned"], default=None)

    # for O&M tasks, indicates if site visit was created
    site_visit_added: bool = Field(examples=[True], description="Indicates if site visit was added or not.")

    completed_at: Optional[datetime] = Field(None, examples=["2024-04-15T11:58:22.183013"])


class TaskDescriptionUpdateSchema(BaseModel):
    description: Optional[str] = Field(
        None, examples=["Please, document inverter #12 metrics"], max_length=TEXT_AREA_MAX_LENGTH
    )


class TaskSummaryOfEventUpdateSchema(BaseModel):
    summary_of_events: Optional[str] = Field(
        examples=["The team of 2 field engineers were assigned"], default=None, max_length=TEXT_AREA_MAX_LENGTH
    )


class TaskDetailsUpdateSchema(TaskCreationPayloadSchema):
    alert_id: ClassVar[int]  # exclude since we don't have an option to edit attached alert ID
    description: ClassVar[str]  # exclude since we update description as separate schema


class TaskUpdateSuccess(Success):
    message: str = Field(description="Success message", examples=[TaskMessages.task_update_success])


class TaskSiteSchema(BaseModel):
    id: int = Field(examples=[1])
    company_id: int = Field(examples=[1])


class TaskCompanySchema(BaseModel):
    id: int = Field(examples=[1])


class TaskDocumentSchema(BaseModel):
    id: int = Field(examples=[1])
    site_id: int = Field(examples=[1])
    company_id: int = Field(examples=[1])


class UserTaskSchema(TaskListViewSchema):
    # Exclude unused fields
    description: ClassVar[str]
    affected_device: ClassVar[TaskAffectedDevice]

    module: BoardModuleEnum
    site: Optional[TaskSiteSchema] = Field(default=None)
    company: Optional[TaskCompanySchema] = Field(default=None)
    document: Optional[TaskDocumentSchema] = Field(default=None)


class UserTasksListResponse(BasePaginator):

    items: list[UserTaskSchema]
