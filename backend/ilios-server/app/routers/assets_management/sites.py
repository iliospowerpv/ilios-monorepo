"""Sites router - READ and Asset Management endpoints only.

Legacy mutation endpoints (POST/PUT/DELETE) for Settings-based site management
have been removed. Site management is now done via Portfolio Admin.
Asset Management detail updates (PUT /{site_id}/details) remain available.
"""
import logging
from copy import deepcopy
from typing import Annotated, Any, Dict, Type, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi_filter import FilterDepends
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.crud.device import DeviceCRUD
from app.crud.site import SiteCRUD
from app.crud.site_additional_fields_list import SiteAdditionalFieldListCRUD
from app.db.object_utils import as_dict
from app.db.session import get_session
from app.filters.device_filters import SearchDeviceByName
from app.filters.site_filters import SiteFilter
from app.helpers.assets_management.assets_management_helper import get_site_cards_with_dd_data
from app.helpers.assets_management.site_details_schema_helper import get_section_schema
from app.helpers.authentication import get_current_user
from app.helpers.authorization import (
    AssetPermissions,
    AuthorizedUser,
    DiligencePermissions,
    OnMPermissions,
    SettingsPermissions,
)
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.bq_data_sync_helper import SiteCharacteristicsHandler
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.models.site import Site
from app.schema.site import (
    AllSitesPaginator,
    BaseSiteSchema,
    ExtendedSiteSchemaWithConnection,
    PotentialAffectedDevicesList,
    SiteOrderByFieldEnum,
    SiteUpdateSuccess,
)
from app.schema.site_details import SiteFullDetailsSchema
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions, SiteMessages
from app.static.sites import SITE_AM_SECTIONS_SCHEMAS, SiteDetailsSections, site_am_sections_doc

logger = logging.getLogger(__name__)
sites_router = APIRouter()


@sites_router.get(
    "/",
    response_model=AllSitesPaginator,
)
async def get(
    query_params: tuple = Depends(validate_query_params(order_by=SiteOrderByFieldEnum)),
    *,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(
            AuthorizedUser([AssetPermissions(PermissionsActions.view), DiligencePermissions(PermissionsActions.view)])
        ),
    ],
    site_filter: SiteFilter = FilterDepends(SiteFilter),
    db_session: Session = Depends(get_session),
) -> dict:
    site_crud = SiteCRUD(db_session)
    skip, limit, order_by, order_direction = query_params
    total, sites = site_crud.filter(
        current_user.get_limited_sites_ids(), site_filter, skip, limit, order_by, order_direction
    )
    response_sites = []

    # extend site payload with values from other sources: due diligence, site additional fields
    for site in sites:
        site_object_fields = as_dict(site)

        # process <site additional fields> table data
        site_details_fields = as_dict(site.additional_fields) if site.additional_fields else {}
        # remove ID field do not overwrite with it real site ID
        site_details_fields.pop("id", None)

        # process due diligence documents data
        site_cards_with_due_diligence = get_site_cards_with_dd_data(site)
        due_diligence_fields = {
            "production_guarantee": site_cards_with_due_diligence["o_and_m"]["production_guarantee"],
            "o_and_m_provider": site_cards_with_due_diligence["o_and_m"]["provider"],
            "utility_provider": site_cards_with_due_diligence["interconnection"]["provider"],
            "epc_provider": site_cards_with_due_diligence["epc_contractor"]["provider"],
        }

        # combine all together into the final site payload
        # since we operate with site as a dict (but backref fields requires model), explicitly add these fields
        merged_site_details = {
            **site_object_fields,
            **site_details_fields,
            **due_diligence_fields,
            "company": site.company,
        }
        response_sites.append(merged_site_details)
    return {"items": response_sites, **pagination_details(skip, limit, total)}


@sites_router.get(
    "/{site_id}",
    response_model=ExtendedSiteSchemaWithConnection,
    responses={**HTTP_404_RESPONSE},
    description="Site info to populate site editing form",
    dependencies=[
        Depends(
            AuthorizedUser(
                [
                    AssetPermissions(PermissionsActions.view),
                    DiligencePermissions(PermissionsActions.view),
                    SettingsPermissions(PermissionsActions.view),
                ]
            )
        )
    ],
)
async def get_by_id(
    site: Site = Depends(get_authorized_site),
):
    return site


@sites_router.get(
    "/{site_id}/details",
    response_model=SiteFullDetailsSchema,
    responses={**HTTP_404_RESPONSE},
    description="Extended site info, with mocked section, to be shown on the site dashboard on Asset Management",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def get_site_details(
    site: Site = Depends(get_authorized_site),
):
    site_cards_with_due_diligence = get_site_cards_with_dd_data(site)
    site_details_fields = as_dict(site.additional_fields) if site.additional_fields else {}

    response = {}
    # for each card, populate it content from general site info OR due diligence OR additional site fields
    for site_details_card_name in SiteDetailsSections:
        payload = site_details_fields
        # check if card appears in the DD cards, and need to be merged with details fields
        due_diligence_details = site_cards_with_due_diligence.get(site_details_card_name.value)
        if due_diligence_details:
            payload = {**payload, **due_diligence_details}
        # special handling of the 'site_level_details', map site level details to site object in common card
        if site_details_card_name == SiteDetailsSections.site_level_details:
            site_object_fields = BaseSiteSchema.model_validate(site).model_dump()
            payload = {**payload, **site_object_fields}

        # finally, add section to the response
        response[site_details_card_name.value] = payload

    return response


@sites_router.put(
    "/{site_id}/details",
    response_model=SiteUpdateSuccess,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**HTTP_404_RESPONSE},
    description="Update additional sites fields section by section. Please, note! Each section has it own schema:"
    f"\n\n{site_am_sections_doc}",
    dependencies=[Depends(AuthorizedUser(AssetPermissions(PermissionsActions.view)))],
)
async def update_site_details(
    # we need to mention each schema to include it to the swagger doc
    data: Union[Dict[str, Any], *SITE_AM_SECTIONS_SCHEMAS],
    section_name: SiteDetailsSections,  # noqa: U100
    background_tasks: BackgroundTasks,
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
    section_schema: Type[BaseModel] = Depends(get_section_schema),
):
    site_details_crud = SiteAdditionalFieldListCRUD(db_session)
    # check if additional fields object needs to be added, or it already exists
    if not site.additional_fields:
        site_details_crud.create_item({"site_id": site.id})

    # make a snapshot for difference comparison
    additional_fields_before_update = deepcopy(as_dict(site.additional_fields))

    try:
        # validate input against chosen schema
        validated_data = section_schema(**data)
    except ValidationError as exc:
        # build the message in the way Pydantic return it when it's validated automatically
        msg = "; ".join(
            [f"{'.'.join(str(loc_) for loc_ in error_['loc'])} - {error_['msg']}" for error_ in exc.errors()]
        )
        raise HTTPException(status_code=422, detail=f"Validation error: {msg}")

    updated_site_details_payload = validated_data.model_dump()
    site_details_crud.update_by_id(site.additional_fields.id, updated_site_details_payload)

    # track changes on Asset Overview and Key Dates card
    if section_name in [SiteDetailsSections.asset_overview, SiteDetailsSections.key_dates]:
        background_tasks.add_task(
            SiteCharacteristicsHandler(site).sync_to_bq,
            old_record=additional_fields_before_update,
            new_record=updated_site_details_payload,
        )

    return {"code": status.HTTP_202_ACCEPTED, "message": SiteMessages.site_update_success}


@sites_router.get(
    "/{site_id}/affected-devices",
    response_model=PotentialAffectedDevicesList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Potential affected devices for task.",
    dependencies=[
        Depends(AuthorizedUser([AssetPermissions(PermissionsActions.view), OnMPermissions(PermissionsActions.view)]))
    ],
)
async def get_potential_affected_devices(
    site: Site = Depends(get_authorized_site),
    search_task_filter: SearchDeviceByName = FilterDepends(SearchDeviceByName),
    db_session: Session = Depends(get_session),
):
    potential_affected_devices = DeviceCRUD(db_session).get_potential_affected_devices(site.id, search_task_filter)
    return {"items": potential_affected_devices}
