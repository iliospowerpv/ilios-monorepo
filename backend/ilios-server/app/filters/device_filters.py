"""Filters for Device model."""

from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter

from app.models.device import Device


class SearchDeviceByName(Filter):
    search: Optional[str] = None

    class Constants(Filter.Constants):
        model = Device
        search_model_fields = ["name"]
