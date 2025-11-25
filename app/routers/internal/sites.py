import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.crud.site import SiteCRUD
from app.crud.site_weather import SiteWeatherCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.schema.om_site import CreateSiteWeatherList, SitesLocationsList
from app.schema.site import SiteUpdateSuccess
from app.static.responses import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_weather_router = APIRouter()


@internal_weather_router.get(
    "/sites/locations",
    dependencies=[Depends(api_key_check)],
    response_model=SitesLocationsList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_sites_locations(
    db_session: Session = Depends(get_session),
):
    return {"data": SiteCRUD(db_session).get_sites_location()}


@internal_weather_router.post(
    "/sites/weather",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_201_CREATED,
    response_model=SiteUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def bulk_create_sites_weather(
    sites_weather_list: CreateSiteWeatherList,
    db_session: Session = Depends(get_session),
):
    SiteWeatherCRUD(db_session).create_items(sites_weather_list.model_dump()["payload"])
    return {"code": status.HTTP_201_CREATED, "message": "Sites weather has been successfully created"}
