from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy.orm import Session

import app.static as static
from app.db.base import Device
from app.models.device import DeviceCategories, DeviceStatuses

from .base_crud import BaseCRUD


class DeviceCRUD(BaseCRUD):
    """CRUD operations on Device model."""

    def __init__(self, db_session: Session):
        super().__init__(model=Device, db_session=db_session)

    def get_site_devices(
        self,
        site_id: int,
        search_filter: Filter | None = None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
        categories: Optional[list[DeviceCategories]] = None,
    ):
        query = self.db_session.query(self.model).filter(self.model.site_id == site_id)
        # Additive, read-only category filter. Each UI category group maps to a set of
        # DeviceCategories on the frontend; here we simply restrict by category. This does
        # NOT touch the telemetry eligibility classifier or what can drive expected.
        if categories:
            query = query.filter(self.model.category.in_(categories))
        if search_filter is not None:
            query = search_filter.filter(query)
        query = self._add_order_by(query, order_by, order_direction)
        total = query.count()

        return total, query.offset(skip).limit(limit).all()

    def get_potential_affected_devices(self, site_id, search_filter: Filter | None = None):
        query = self.db_session.query(self.model.id, self.model.name).filter(self.model.site_id == site_id)
        query = query.filter(self.model.status != DeviceStatuses.decommissioned)
        if search_filter:
            query = search_filter.filter(query)
        query = self._add_order_by(query, None, None)
        return query.all()
