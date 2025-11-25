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
