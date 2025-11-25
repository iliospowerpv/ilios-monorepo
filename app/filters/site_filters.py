"""Filters for Site model."""

from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter

from app.models.site import Site, State


class SiteFilter(Filter):
    company_id: Optional[int] = None
    state: Optional[State] = None

    search: Optional[str] = None

    class Constants(Filter.Constants):
        model = Site
        search_model_fields = ["name"]


class SearchSiteByName(Filter):
    search: Optional[str] = None

    class Constants(Filter.Constants):
        model = Site
        search_model_fields = ["name"]
