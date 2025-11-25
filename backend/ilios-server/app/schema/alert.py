import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.alert import AlertSeverity
from app.schema.board_statuses import StatusItemSchema
from app.schema.paginator import BasePaginator
from app.static import AlertMessages


class AlertCreationSuccess(BaseModel):
    message: str = Field(description="Success message", examples=[AlertMessages.alert_create_success])
    code: int = Field(description="Success status code", examples=[201])


class AlertBaseSchema(BaseModel):
    id: int = Field(examples=[1])
    severity: AlertSeverity
    alert_start: datetime
    alert_end: Optional[datetime] = Field(None, examples=[datetime.now()])


class AlertTaskSchema(BaseModel):
    id: int = Field(examples=[1])
    external_id: str = Field(examples=["IOSP1-894"])
    status: Optional[StatusItemSchema]


class AlertsPageSchema(AlertBaseSchema):
    """Model of fields for the page of alerts listing"""

    device_id: int = Field(examples=[2])
    is_resolved: bool = Field(examples=[False])
    type: str
    error_message: str
    Task: Optional[AlertTaskSchema] = Field(default=None, serialization_alias="task")


class SiteAlertsPageSchema(AlertsPageSchema):
    device_name: str


class CompanyAlertsPageSchema(SiteAlertsPageSchema):
    site_name: str
    site_id: int = Field(examples=[1])


class DeviceAlertsPaginator(BasePaginator):
    """Alerts schema along pagination fields included"""

    items: list[AlertsPageSchema]


class SiteAlertsPaginator(BasePaginator):
    """Alerts schema along pagination fields included"""

    items: list[SiteAlertsPageSchema]


class CompanyAlertsPaginator(BasePaginator):
    """Alerts schema along pagination fields included"""

    items: list[CompanyAlertsPageSchema]


class AlertEditSuccess(BaseModel):
    message: str = Field(description="Success message", examples=[AlertMessages.alert_update_success])
    code: int = Field(description="Success status code", examples=[204])


class AlertOverviewSchema(BaseModel):
    severity: AlertSeverity
    total: int = Field(examples=[10])


class AlertDashboardOverviewSchema(AlertOverviewSchema):
    unaccomplished_tasks_count: Optional[int] = Field(examples=[1], default=0)


class DeviceAlertsOrderByFieldEnum(str, enum.Enum):
    severity = "severity"
    alert_start = "alert_start"
    type = "type"


class SiteAlertsOrderByFieldEnum(str, enum.Enum):
    severity = "severity"
    alert_start = "alert_start"
    type = "type"
    device_name = "device_name"


class CompanyAlertsOrderByFieldEnum(str, enum.Enum):
    severity = "severity"
    alert_start = "alert_start"
    type = "type"
    device_name = "device_name"
    site_name = "site_name"


class AlertCreateSchema(BaseModel):
    device_id: int = Field(examples=[2])
    severity: AlertSeverity = Field(examples=["high"])
    alert_start: datetime = Field(examples=[datetime.now()])
    type: str = Field(examples=["inverter_energy_ratio"])
    is_resolved: Optional[bool] = Field(False, examples=[False])
    error_message: str = Field(examples=["device connection failed"])
    external_id: str = Field(examples=["121w2DFw"])


class OMAlertSchema(AlertBaseSchema):
    type: str
