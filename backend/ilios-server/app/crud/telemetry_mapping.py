from app.crud.base_crud import BaseCRUD
from app.models.telemetry import TelemetryDeviceMapping, TelemetrySiteMapping


class TelemetrySiteMappingCRUD(BaseCRUD):
    """CRUD operations on TelemetrySiteMapping model."""

    def __init__(self, db_session):
        super().__init__(model=TelemetrySiteMapping, db_session=db_session)


class TelemetryDeviceMappingCRUD(BaseCRUD):
    """CRUD operations on TelemetryDeviceMapping model."""

    def __init__(self, db_session):
        super().__init__(model=TelemetryDeviceMapping, db_session=db_session)
