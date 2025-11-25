"""Filters for Task model."""

from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter

from app.models.task import Task


class SearchTaskByName(Filter):
    search: Optional[str] = None

    class Constants(Filter.Constants):
        model = Task
        search_model_fields = ["name"]
