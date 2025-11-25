"""CRUD operations on SiteWeather model."""

from app.crud.base_crud import BaseCRUD
from app.models.site import SiteWeather


class SiteWeatherCRUD(BaseCRUD):
    """CRUD operations on SiteWeather model."""

    def __init__(self, db_session):
        super().__init__(model=SiteWeather, db_session=db_session)
