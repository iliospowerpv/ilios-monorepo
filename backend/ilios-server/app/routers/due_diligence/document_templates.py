"""Data Room Templates router (Task #91).

Reusable, company-scoped snapshots of a Data Room's *structure* (stages, expected
documents, ordering, descriptions, guidance, optionality — never files/versions/
metadata/approvals/history). Everything lives inside the existing Data Room surface:
all endpoints are nested under a site so authorization reuses the canonical site
resolver + the existing ``Diligence`` module permission. Templates themselves are
company-scoped (visible to every project in the company that owns them).

Applying a template to scaffold a *new* Data Room happens through the existing
site-creation path (see ``CreateSiteSchema.template_id``), not here — this router
only manages templates (create / duplicate / rename / archive / delete / import /
export). The canonical ``Site`` entity is untouched (Project == Site is a UI label).
"""
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.data_room_template import DataRoomTemplateCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.due_diligence.data_room_templates import (
    TemplateStructureError,
    parse_imported_template,
    serialize_template,
    snapshot_default_structure,
    snapshot_site_structure,
    validate_template_structure,
)
from app.helpers.permission_guards import require_module_permission
from app.models.site import Site
from app.schema.data_room_templates import (
    CreateTemplateFromDataRoomSchema,
    CreateTemplateSchema,
    DuplicateTemplateSchema,
    ImportTemplateSchema,
    TemplateDetailSchema,
    TemplateExportSchema,
    TemplateListSchema,
    TemplateMutationSuccess,
    UpdateTemplateSchema,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE
from app.static.permissions import PermissionsModules

logger = logging.getLogger(__name__)
document_templates_router = APIRouter()


def _require_view(current_user: CurrentUserSchema, site: Site, db_session: Session) -> None:
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        db_session=db_session,
        module_key=PermissionsModules.diligence.value,
        action="view",
        project_id=site.id,
    )


def _require_edit(current_user: CurrentUserSchema, site: Site, db_session: Session) -> None:
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        db_session=db_session,
        module_key=PermissionsModules.diligence.value,
        action="edit",
        project_id=site.id,
    )


def _counts(structure: dict) -> tuple[int, int]:
    sections = structure.get("sections", []) if isinstance(structure, dict) else []
    section_count = len(sections)
    document_count = 0
    for section in sections:
        document_count += len(section.get("documents", []) or [])
        for sub in section.get("subsections", []) or []:
            document_count += len(sub.get("documents", []) or [])
    return section_count, document_count


def _summary(template) -> dict:
    section_count, document_count = _counts(template.structure or {})
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "is_archived": template.is_archived,
        "section_count": section_count,
        "document_count": document_count,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


def _detail(template) -> dict:
    data = _summary(template)
    data["structure"] = template.structure or {"version": 1, "sections": []}
    return data


def _get_scoped_template(template_id: int, site: Site, db_session: Session):
    template = DataRoomTemplateCRUD(db_session).get_for_company(template_id, site.company_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template not found")
    return template


@document_templates_router.get(
    "/",
    response_model=TemplateListSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def list_templates(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    include_archived: bool = False,
    db_session: Session = Depends(get_session),
) -> dict:
    _require_view(current_user, site, db_session)
    templates = DataRoomTemplateCRUD(db_session).get_by_company(site.company_id, include_archived=include_archived)
    return {"items": [_summary(t) for t in templates]}


@document_templates_router.get(
    "/{template_id}",
    response_model=TemplateDetailSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_template(
    template_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    _require_view(current_user, site, db_session)
    template = _get_scoped_template(template_id, site, db_session)
    return _detail(template)


@document_templates_router.get(
    "/{template_id}/export",
    response_model=TemplateExportSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def export_template(
    template_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    _require_view(current_user, site, db_session)
    template = _get_scoped_template(template_id, site, db_session)
    return serialize_template(template)


@document_templates_router.post(
    "/from-data-room",
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateMutationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def create_template_from_data_room(
    payload: CreateTemplateFromDataRoomSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    """Capture this site's *current* Data Room structure as a reusable template."""
    _require_edit(current_user, site, db_session)
    structure = snapshot_site_structure(site.id, db_session)
    template = DataRoomTemplateCRUD(db_session).create_item(
        {
            "company_id": site.company_id,
            "created_by_id": current_user.id,
            "name": payload.name.strip(),
            "description": payload.description,
            "structure": structure,
        }
    )
    return {"code": 201, "id": template.id, "message": "Template has been created"}


@document_templates_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateMutationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def create_template(
    payload: CreateTemplateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    """Create a template from a supplied structure, or the canonical default blueprint."""
    _require_edit(current_user, site, db_session)
    try:
        structure = (
            validate_template_structure(payload.structure)
            if payload.structure is not None
            else snapshot_default_structure()
        )
    except TemplateStructureError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    template = DataRoomTemplateCRUD(db_session).create_item(
        {
            "company_id": site.company_id,
            "created_by_id": current_user.id,
            "name": payload.name.strip(),
            "description": payload.description,
            "structure": structure,
        }
    )
    return {"code": 201, "id": template.id, "message": "Template has been created"}


@document_templates_router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateMutationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def import_template(
    payload: ImportTemplateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    _require_edit(current_user, site, db_session)
    try:
        parsed = parse_imported_template(payload.payload)
    except TemplateStructureError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    name = (payload.name or parsed["name"]).strip()
    template = DataRoomTemplateCRUD(db_session).create_item(
        {
            "company_id": site.company_id,
            "created_by_id": current_user.id,
            "name": name,
            "description": parsed["description"],
            "structure": parsed["structure"],
        }
    )
    return {"code": 201, "id": template.id, "message": "Template has been imported"}


@document_templates_router.post(
    "/{template_id}/duplicate",
    status_code=status.HTTP_201_CREATED,
    response_model=TemplateMutationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def duplicate_template(
    template_id: int,
    payload: DuplicateTemplateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    _require_edit(current_user, site, db_session)
    source = _get_scoped_template(template_id, site, db_session)
    name = (payload.name.strip() if payload.name else f"{source.name} (Copy)")
    template = DataRoomTemplateCRUD(db_session).create_item(
        {
            "company_id": site.company_id,
            "created_by_id": current_user.id,
            "name": name,
            "description": source.description,
            # Deep-copy the structure via JSON round-trip so the duplicate is independent.
            "structure": json.loads(json.dumps(source.structure)),
        }
    )
    return {"code": 201, "id": template.id, "message": "Template has been duplicated"}


@document_templates_router.put(
    "/{template_id}",
    response_model=TemplateMutationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def update_template(
    template_id: int,
    payload: UpdateTemplateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    _require_edit(current_user, site, db_session)
    template = _get_scoped_template(template_id, site, db_session)
    updates: dict = {}
    if payload.name is not None:
        updates["name"] = payload.name.strip()
    if payload.description is not None:
        updates["description"] = payload.description
    if updates:
        DataRoomTemplateCRUD(db_session).update_by_id(template.id, updates)
    return {"code": 200, "id": template.id, "message": "Template has been updated"}


@document_templates_router.post(
    "/{template_id}/archive",
    response_model=TemplateMutationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def archive_template(
    template_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    _require_edit(current_user, site, db_session)
    template = _get_scoped_template(template_id, site, db_session)
    DataRoomTemplateCRUD(db_session).update_by_id(template.id, {"is_archived": True})
    return {"code": 200, "id": template.id, "message": "Template has been archived"}


@document_templates_router.post(
    "/{template_id}/restore",
    response_model=TemplateMutationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def restore_template(
    template_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    _require_edit(current_user, site, db_session)
    template = _get_scoped_template(template_id, site, db_session)
    DataRoomTemplateCRUD(db_session).update_by_id(template.id, {"is_archived": False})
    return {"code": 200, "id": template.id, "message": "Template has been restored"}


@document_templates_router.delete(
    "/{template_id}",
    response_model=TemplateMutationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def delete_template(
    template_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> dict:
    _require_edit(current_user, site, db_session)
    template = _get_scoped_template(template_id, site, db_session)
    DataRoomTemplateCRUD(db_session).delete_by_id(template.id)
    return {"code": 200, "id": template_id, "message": "Template has been deleted"}
