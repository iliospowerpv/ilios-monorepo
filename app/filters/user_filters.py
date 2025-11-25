"""Filters for User model."""

from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter

from app.models.user import User


class UserSearchFilter(Filter):
    search: Optional[str] = None

    class Constants(Filter.Constants):
        model = User
        search_model_fields = ["first_name", "last_name", "email"]


class UserSearchForTaskFilter(Filter):
    search: Optional[str] = None

    class Constants(Filter.Constants):
        model = User
        search_model_fields = ["first_name", "last_name"]
