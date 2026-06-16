"""Sites router - READ, CREATE, and Asset Management endpoints.

Authorization Pattern (Phase C.1):
- Entity access: get_authorized_site (canonical resolver, fail-closed)
- Module permission: require_module_permission (assets_management:view/edit)
- Order: Entity check first, then module permission check
- Creation: require_module_permission at company level (no site_id yet)
"""
import logging
from copy import deepcopy
from datetime import datetime
from typing import Annotated, Any, Dict, Type, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi_filter import FilterDepends
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.audit_log import AuditLogCRUD
from app.crud.device import DeviceCRUD
from app.crud.document import DocumentCRUD
from app.crud.site import SiteCRUD
from app.crud.site_additional_fields_list import SiteAdditionalFieldListCRUD
from app.crud.user_project import UserProjectCRUD
from app.db.object_utils import as_dict
from app.db.session import get_session
from app.filters.device_filters import SearchDeviceByName
from app.filters.site_filters import SiteFilter
from app.helpers.assets_management.assets_management_helper import get_site_cards_with_dd_data
from app.helpers.assets_management.site_details_schema_helper import get_section_schema
from app.helpers.authentication import get_current_user
from app.helpers.authorization.module_based.base import get_current_admin_user
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.bq_data_sync_helper import SiteCharacteristicsHandler
from app.helpers.due_diligence.due_diligence_helper import (
    create_default_site_document_sections,
    generate_default_site_documents,
)
from app.helpers.pagination import pagination_details
from app.helpers.permission_guards import require_module_permission, require_module_permission_any_context
from app.helpers.query_params_validator import validate_query_params
from app.helpers.task_tracker.board_defaults_helper import create_default_board, create_default_document_tasks
from app.models.board import BoardModuleEnum, BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.models.company import Company
from app.models.site import Site
from app.schema.site import (
    AllSitesPaginator,
    BaseSiteSchema,
    CreateSiteSchema,
    ExtendedSiteSchemaWithConnection,
    PotentialAffectedDevicesList,
    SiteCreationResponse,
    SiteOrderByFieldEnum,
    SiteUpdateSuccess,
    UpdateSiteSchema,
)
from app.schema.site_details import SiteFullDetailsSchema
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, SiteMessages
from app.static.permissions import PermissionsModules
from app.static.sites import (
    PROTECTED_BASELINE_DRIVING_FIELDS,
    SITE_AM_SECTIONS_SCHEMAS,
    SiteDetailsSections,
    site_am_sections_doc,
)

logger = logging.getLogger(__name__)
sites_router = APIRouter()


@sites_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=SiteCreationResponse,
    responses={**HTTP_403_RESPONSE},
)
async def create(
    site: CreateSiteSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> dict:
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="edit",
    )

    site_data = site.model_dump()
    try:
        new_site = SiteCRUD(db_session).create_item(site_data)
        logger.info(f"Created site with id {new_site.id}")
    except IntegrityError:
        logger.exception(message := f"Company with ID: {site.company_id} not found.")
        raise HTTPException(status.HTTP_404_NOT_FOUND, message)

    create_default_site_document_sections([new_site.id], db_session)
    DocumentCRUD(db_session).create_items(generate_default_site_documents([new_site.id], db_session))

    create_default_board(new_site.id, BoardRelatedEntityTypeEnum.site, db_session)
    create_default_board(new_site.id, BoardRelatedEntityTypeEnum.site, db_session, module=BoardModuleEnum.om)
    create_default_board(
        new_site.id, BoardRelatedEntityTypeEnum.site, db_session, BoardRelatedEntityTypeExtraEnum.document
    )
    create_default_document_tasks(
        db_session, new_site.documents_board, new_site.documents, current_user.id, freeze_external_id=True
    )

    if not current_user.has_platform_bypass:
        UserProjectCRUD(db_session).create_item(
            {"user_id": current_user.id, "site_id": new_site.id, "company_id": new_site.company_id}
        )

    return {"code": 201, "message": "Site has been created", "id": new_site.id}


@sites_router.get(
    "/",
    response_model=AllSitesPaginator,
    responses={**HTTP_403_RESPONSE},
)
async def get(
    query_params: tuple = Depends(validate_query_params(order_by=SiteOrderByFieldEnum)),
    *,
    is_archived: bool = Query(False, description="Show only archived projects"),
    include_all: bool = Query(False, description="Show both active and archived projects"),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site_filter: SiteFilter = FilterDepends(SiteFilter),
    db_session: Session = Depends(get_session),
) -> dict:
    if not current_user.has_platform_bypass:
        if is_archived or include_all:
            raise HTTPException(status_code=403, detail="Only system users can view archived projects")
        require_module_permission_any_context(
            user_id=current_user.id,
            company_ids=current_user.get_limited_companies_ids(),
            site_ids=current_user.get_limited_sites_ids(),
            db_session=db_session,
            module_key=PermissionsModules.assets_management.value,
            action="view",
        )
    site_crud = SiteCRUD(db_session)
    skip, limit, order_by, order_direction = query_params
    total, sites = site_crud.filter(
        current_user.get_limited_sites_ids(), site_filter, skip, limit, order_by, order_direction,
        include_archived=include_all,
        archived_only=is_archived,
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
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Site info to populate site editing form",
)
async def get_by_id(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="view",
        project_id=site.id,
    )
    return site


@sites_router.get(
    "/{site_id}/details",
    response_model=SiteFullDetailsSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Extended site info, with mocked section, to be shown on the site dashboard on Asset Management",
)
async def get_site_details(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="view",
        project_id=site.id,
    )
    site_cards_with_due_diligence = get_site_cards_with_dd_data(site)
    site_details_fields = as_dict(site.additional_fields) if site.additional_fields else {}

    response = {}
    for site_details_card_name in SiteDetailsSections:
        payload = site_details_fields
        due_diligence_details = site_cards_with_due_diligence.get(site_details_card_name.value)
        if due_diligence_details:
            payload = {**payload, **due_diligence_details}
        if site_details_card_name == SiteDetailsSections.site_level_details:
            site_object_fields = BaseSiteSchema.model_validate(site).model_dump()
            payload = {**payload, **site_object_fields}

        response[site_details_card_name.value] = payload

    entity_assignments = []
    for rel in site.entity_relationships:
        entity_assignments.append({
            "id": rel.id,
            "entity_id": rel.entity_id,
            "entity_name": rel.entity.name if rel.entity else None,
            "entity_type": rel.entity.entity_type.value if rel.entity and rel.entity.entity_type else None,
            "role": rel.role.value if rel.role else None,
            "contact_id": rel.contact_id,
            "contact_name": f"{rel.contact.first_name} {rel.contact.last_name}" if rel.contact else None,
            "effective_date": rel.effective_date,
            "termination_date": rel.termination_date,
            "notes": rel.notes,
        })
    response["entity_assignments"] = entity_assignments

    return response


@sites_router.put(
    "/{site_id}",
    response_model=SiteCreationResponse,
    status_code=status.HTTP_200_OK,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description=(
        "Update a site's core attributes (name, address, system sizes, timezone, etc.). "
        "Full-replace semantics: the request body is applied as-is, so omitting an optional "
        "field (e.g. timezone, cameras_uuids) resets it to its schema default. Always send the "
        "complete current values. ``company_id`` is accepted but ignored (a site is never re-parented)."
    ),
)
async def update_site(
    data: UpdateSiteSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="edit",
        project_id=site.id,
    )
    # ``company_id`` may be echoed back by the edit form; ignore it so the site
    # is never re-parented to a different company.
    update_payload = data.model_dump(exclude={"company_id"})
    SiteCRUD(db_session).update_by_id(site.id, update_payload)
    return {
        "id": site.id,
        "code": status.HTTP_200_OK,
        "message": SiteMessages.site_update_success,
    }


@sites_router.put(
    "/{site_id}/details",
    response_model=SiteUpdateSuccess,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Update additional sites fields section by section. Please, note! Each section has it own schema:"
    f"\n\n{site_am_sections_doc}",
)
async def update_site_details(
    data: Union[Dict[str, Any], *SITE_AM_SECTIONS_SCHEMAS],
    section_name: SiteDetailsSections,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
    section_schema: Type[BaseModel] = Depends(get_section_schema),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="edit",
        project_id=site.id,
    )
    site_details_crud = SiteAdditionalFieldListCRUD(db_session)
    if not site.additional_fields:
        site_details_crud.create_item({"site_id": site.id})

    additional_fields_before_update = deepcopy(as_dict(site.additional_fields))

    try:
        validated_data = section_schema(**data)
    except ValidationError as exc:
        msg = "; ".join(
            [f"{'.'.join(str(loc_) for loc_ in error_['loc'])} - {error_['msg']}" for error_ in exc.errors()]
        )
        raise HTTPException(status_code=422, detail=f"Validation error: {msg}")

    updated_site_details_payload = validated_data.model_dump()

    # Phase 1+2 safety guard: baseline-driving fields are owned by the Data Room / promoted
    # project-facts provenance chain and are rendered read-only in the Project Hub Overview.
    # Strip them from the persisted payload (defense-in-depth, even if a client still sends them)
    # so existing SiteAdditionalFieldList values are preserved and never blanked.
    protected_fields = PROTECTED_BASELINE_DRIVING_FIELDS.get(section_name, set())
    blocked_fields = [field for field in protected_fields if field in updated_site_details_payload]
    if blocked_fields:
        logger.warning(
            "Ignoring write to protected baseline-driving field(s) %s on site %s section '%s'; "
            "these values are managed through the Data Room provenance chain.",
            sorted(blocked_fields),
            site.id,
            section_name.value,
        )
    persisted_payload = {
        key: value for key, value in updated_site_details_payload.items() if key not in protected_fields
    }
    site_details_crud.update_by_id(site.additional_fields.id, persisted_payload)

    if section_name in [SiteDetailsSections.asset_overview, SiteDetailsSections.key_dates]:
        # Protected baseline-driving fields are stripped above, so the site-characteristics diff
        # surfaces no BigQuery-mapped changes and this sync is a guaranteed no-op for these
        # sections. The mechanism is intentionally left in place (unchanged) for any future,
        # non-protected site characteristic.
        background_tasks.add_task(
            SiteCharacteristicsHandler(site).sync_to_bq,
            old_record=additional_fields_before_update,
            new_record=persisted_payload,
        )

    return {"code": status.HTTP_202_ACCEPTED, "message": SiteMessages.site_update_success}


@sites_router.get(
    "/{site_id}/affected-devices",
    response_model=PotentialAffectedDevicesList,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Potential affected devices for task.",
)
async def get_potential_affected_devices(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    search_task_filter: SearchDeviceByName = FilterDepends(SearchDeviceByName),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="view",
        project_id=site.id,
    )
    potential_affected_devices = DeviceCRUD(db_session).get_potential_affected_devices(site.id, search_task_filter)
    return {"items": potential_affected_devices}


@sites_router.patch(
    "/{site_id}/archive",
    status_code=status.HTTP_200_OK,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def archive_site(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    if site.is_archived:
        return {"message": "Project is already archived", "id": site.id}

    now = datetime.utcnow()
    site.is_archived = True
    site.archived_at = now
    site.archived_by = current_user.id
    site.cascade_archived_by_company = False

    audit_crud = AuditLogCRUD(db_session)
    audit_crud.create_item({
        "source": "sites",
        "action": f"Archived project '{site.name}' (ID: {site.id})",
        "is_success": True,
        "details": f"Project archived by admin.",
        "user_id": current_user.id,
    })

    db_session.commit()
    return {"message": f"Project '{site.name}' archived", "id": site.id}


@sites_router.patch(
    "/{site_id}/restore",
    status_code=status.HTTP_200_OK,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def restore_site(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    if not site.is_archived:
        return {"message": "Project is already active", "id": site.id}

    company = db_session.query(Company).get(site.company_id)
    if company and company.is_archived:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot restore project while its parent company is archived. Restore the company first.",
        )

    site.is_archived = False
    site.archived_at = None
    site.archived_by = None
    site.cascade_archived_by_company = False

    audit_crud = AuditLogCRUD(db_session)
    audit_crud.create_item({
        "source": "sites",
        "action": f"Restored project '{site.name}' (ID: {site.id})",
        "is_success": True,
        "details": f"Project restored by admin.",
        "user_id": current_user.id,
    })

    db_session.commit()
    return {"message": f"Project '{site.name}' restored", "id": site.id}
