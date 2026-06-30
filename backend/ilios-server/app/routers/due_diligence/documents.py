"""Module to manage due diligence requirement (DDR) objects, previously called documents"""

import logging
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.audit_log import AuditLogCRUD
from app.crud.document import DocumentCRUD
from app.crud.document_key import DocumentKeyCRUD
from app.crud.document_section import DocumentSectionCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_document, get_authorized_site
from app.helpers.permission_guards import require_module_permission
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.configs.co_terminus_helper import CoTerminusHandler
from app.helpers.due_diligence.document_sections_handler import DocumentSectionsHandler
from app.helpers.due_diligence.document_matching import IdentityCandidate, find_duplicate_candidates
from app.helpers.due_diligence.due_diligence_helper import validate_document_section
from app.helpers.due_diligence.expected_documents import get_expected_documents_for_section
from app.helpers.due_diligence.override_guardrail import evaluate_baseline_override
from app.helpers.roles_documents_mapping.handlers_factory import RoleDocumentsHandlerFactory
from app.helpers.task_tracker import TaskTrackerHandlerFactory
from app.helpers.task_tracker.board_defaults_helper import create_default_board, create_default_document_tasks
from app.models.board import BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.models.document import Document
from app.models.site import Site
from app.schema.documents import (
    CustomDocumentCreationSchema,
    DocumentArchiveSchema,
    DocumentArchiveSuccess,
    DocumentCreationSchema,
    DocumentCreationSuccess,
    DocumentDetailsSchema,
    DocumentKeyPoisonPillSchema,
    DocumentKeyUpdateSchema,
    DocumentKeyUpdateSuccess,
    DocumentRemovalSuccess,
    DocumentReorderSchema,
    DocumentUpdateSuccess,
    DuplicateCheckResultSchema,
    ExpectedDocumentsSectionSchema,
    SiteDataRoomGuidanceSchema,
    SiteExpectedDocumentsSchema,
    UpdateDocumentDescriptionSchema,
    UpdateDocumentDetailsSchema,
)
from app.services.due_diligence.data_room_guidance_service import DataRoomGuidanceService
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, DocumentMessages
from app.static.baseline_driving_fields import is_baseline_driving_field
from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

logger = logging.getLogger(__name__)
documents_router = APIRouter()


@documents_router.get(
    "/expected-documents",
    response_model=SiteExpectedDocumentsSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description=(
        "Read-only, per-stage Expected Documents definition for the site's Data Room (Task #90). "
        "Declarative only — it never creates placeholder documents or files."
    ),
)
async def get_expected_documents(
    *,
    site: Site = Depends(get_authorized_site),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        project_id=site.id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
    # Map each site section enum -> its row id so the FE can correlate expectations
    # with the existing section tree. Expectations are static; section ids are per-site.
    site_sections = DocumentSectionCRUD(db_session).get_site_sections(site.id)
    section_id_by_key = {section.name.name: section.id for section in site_sections}

    items = []
    for section in DocumentSections:
        expected = get_expected_documents_for_section(section)
        if not expected:
            continue
        items.append(
            ExpectedDocumentsSectionSchema(
                section_id=section_id_by_key.get(section.name),
                section_key=section.name,
                section_name=section.value,
                expected_documents=expected,
            )
        )
    return {"items": items}


@documents_router.get(
    "/duplicate-check",
    response_model=DuplicateCheckResultSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description=(
        "Read-only, advisory duplicate detection for guided upload (Task #92). Compares a proposed "
        "document name against existing Document Identities for the site (exact + fuzzy near-match) so "
        "the caller can choose to upload a new version to an existing identity instead of creating a "
        "second one. It NEVER blocks, mutates, or creates anything."
    ),
)
async def check_duplicate_document(
    *,
    name: str,
    site: Site = Depends(get_authorized_site),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        project_id=site.id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    documents = DocumentCRUD(db_session).get_site_documents_ordered_by_name(site.id)
    candidates = []
    for document in documents:
        names = [n for n in [document.identity_name, *document.identity_aliases] if n]
        # Include the raw enum value so an aliased/custom-named identity still
        # matches on its underlying canonical document type.
        if document.name and document.name.value not in names:
            names.append(document.name.value)
        candidates.append(
            IdentityCandidate(
                document_id=document.id,
                display_name=document.identity_name or "",
                names=names,
                kind=document.identity_kind,
                section_id=document.section_id,
                section_name=document.section.name.value if document.section and document.section.name else None,
                files_count=document.files_count,
                is_archived=document.is_archived,
            )
        )

    matches = find_duplicate_candidates(name, candidates)
    return {
        "proposed_name": name,
        "has_match": bool(matches),
        "candidates": [vars(match) for match in matches],
    }


@documents_router.get(
    "/guidance",
    response_model=SiteDataRoomGuidanceSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description=(
        "Read-only per-stage Data Room guidance dashboard (Task #92). Surfaces Expected / Present / "
        "Missing / Needs Update / Optional / Archived / Version Count / Promotion Status derived ONLY "
        "from the static Expected Documents catalog and existing document/version/promotion state. "
        "It introduces no new status storage and never writes anything."
    ),
)
async def get_data_room_guidance(
    *,
    site: Site = Depends(get_authorized_site),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        project_id=site.id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
    return DataRoomGuidanceService(db_session).build_guidance(site.id)


@documents_router.get(
    "/{document_id}",
    response_model=DocumentDetailsSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_by_id(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
    document.display_working_zone = document.name.value in AIParsingHandler(db_session).get_parsable_documents_list()
    # Surface the formalized Document Identity (Task #90) additively.
    document.identity = {
        "document_id": document.id,
        "kind": document.identity_kind,
        "canonical_name": document.identity_name,
        "aliases": document.identity_aliases,
    }
    return document


@documents_router.post(
    "/{document_id}/description",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Set document description. To unset the description, send it empty (null)",
)
async def description_update(
    description: UpdateDocumentDescriptionSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    DocumentCRUD(db_session).update_by_id(document.id, description.model_dump())
    return {"code": status.HTTP_202_ACCEPTED, "message": DocumentMessages.document_update_success}


@documents_router.post(
    "/{document_id}/details",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Set/unset document approver",
)
async def details_update(
    document_details: UpdateDocumentDetailsSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    if not document.task:
        logger.warning(f"There is no default task attached to the document with id '{document.id}'")
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED, detail="Cannot associate document with task"
        )
    # (we cannot fully reuse task tracker 'validate_task_assignee_id' method
    # because of it tight connection with the Task model)
    if document_details.approver_id and document.approver_id != document_details.approver_id:
        handler = TaskTrackerHandlerFactory(db_session).get_instance(document.task.board)
        if document_details.approver_id not in handler.get_board_active_users_ids(document.task.id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid approver ID")

    DocumentCRUD(db_session).update_by_id(document.id, document_details.model_dump())
    return {"code": status.HTTP_202_ACCEPTED, "message": DocumentMessages.document_update_success}


@documents_router.get(
    "/",
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_site_documents(
    *,
    site: Site = Depends(get_authorized_site),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        project_id=site.id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    site_sections = DocumentSectionCRUD(db_session).get_site_sections(site.id)
    role_documents_settings = RoleDocumentsHandlerFactory().get_instance(current_user)
    document_section_handler = DocumentSectionsHandler(site_sections, db_session, role_documents_settings)
    return {"items": document_section_handler.generate_site_documents_response()}


@documents_router.post(
    "/",
    response_model=DocumentCreationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def create(
    document: DocumentCreationSchema,
    *,
    site: Site = Depends(get_authorized_site),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        project_id=site.id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    document_payload = document.model_dump()
    # Validate document is attached to correct section
    try:
        validate_document_section(document_payload["name"], document_payload["section_id"], db_session)
    except ValueError as error_msg:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_msg)
    document_payload.update({"site_id": site.id})
    document_data = DocumentCRUD(db_session).create_item(document_payload)
    logger.info(f"Created document with id {document_data.id}")
    # each site document should have linked default ticket
    if not site.documents_board:
        create_default_board(
            site.id, BoardRelatedEntityTypeEnum.site, db_session, BoardRelatedEntityTypeExtraEnum.document
        )
    create_default_document_tasks(db_session, site.documents_board, [document_data], current_user.id)
    return {"code": status.HTTP_201_CREATED, "message": DocumentMessages.document_create_success}


@documents_router.delete(
    "/{document_id}",
    response_model=DocumentRemovalSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def remove_document(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    document: Document = Depends(get_authorized_document),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    from datetime import datetime, timedelta, timezone

    # Check if document has any non-deleted uploaded files
    active_files = [f for f in document.files if not f.deleted]

    if active_files:
        # Check if within 24-hour grace period (based on most recent file upload)
        most_recent_upload = max(f.created_at for f in active_files)
        grace_period_end = most_recent_upload + timedelta(hours=24)
        now = datetime.now(timezone.utc)

        # Make most_recent_upload timezone-aware if it isn't
        if most_recent_upload.tzinfo is None:
            most_recent_upload = most_recent_upload.replace(tzinfo=timezone.utc)
            grace_period_end = most_recent_upload + timedelta(hours=24)

        if now > grace_period_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=DocumentMessages.document_delete_grace_period_expired,
            )

    DocumentCRUD(db_session).delete_by_id(document.id)
    return {"code": status.HTTP_200_OK, "message": DocumentMessages.document_remove_success}


@documents_router.post(
    "/{document_id}/archive",
    status_code=status.HTTP_200_OK,
    response_model=DocumentArchiveSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Archive a document (soft delete). Use this for documents with uploaded files.",
)
async def archive_document(
    payload: DocumentArchiveSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    document: Document = Depends(get_authorized_document),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    DocumentCRUD(db_session).update_by_id(document.id, {"is_archived": True})

    AuditLogCRUD(db_session).create_item({
        "source": "due_diligence_documents",
        "action": f"Archived document (ID: {document.id}) on project (ID: {document.site_id})",
        "is_success": True,
        "details": payload.note,
        "user_id": current_user.id,
    })

    return {"code": status.HTTP_200_OK, "message": DocumentMessages.document_archive_success}


@documents_router.post(
    "/{document_id}/reorder",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Update document position within its section",
)
async def reorder_document(
    reorder_data: DocumentReorderSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    document: Document = Depends(get_authorized_document),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    DocumentCRUD(db_session).update_by_id(document.id, {"position": reorder_data.position})
    return {"code": status.HTTP_202_ACCEPTED, "message": DocumentMessages.document_reorder_success}


@documents_router.post(
    "/custom",
    response_model=DocumentCreationSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Create a custom document with a user-defined name",
)
async def create_custom_document(
    document: CustomDocumentCreationSchema,
    *,
    site: Site = Depends(get_authorized_site),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        project_id=site.id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    # Validate section belongs to the site
    section = DocumentSectionCRUD(db_session).get_by_id(document.section_id)
    if not section or section.site_id != site.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid section ID for this site",
        )

    # Get max position for the section to place new document at the end
    existing_docs = [d for d in section.documents if not d.is_archived]
    max_position = max((d.position for d in existing_docs), default=0)

    document_payload = {
        "site_id": site.id,
        "section_id": document.section_id,
        "name": SiteDocumentsEnum.custom,
        "custom_name": document.custom_name,
        "description": document.description,
        "position": max_position + 1,
    }

    document_data = DocumentCRUD(db_session).create_item(document_payload)
    logger.info(f"Created custom document with id {document_data.id}")

    # each site document should have linked default ticket
    if not site.documents_board:
        create_default_board(
            site.id, BoardRelatedEntityTypeEnum.site, db_session, BoardRelatedEntityTypeExtraEnum.document
        )
    create_default_document_tasks(db_session, site.documents_board, [document_data], current_user.id)

    return {"code": status.HTTP_201_CREATED, "message": DocumentMessages.document_create_success}


@documents_router.put(
    "/{document_id}/keys",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocumentKeyUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Save value of document key depending on the document kind. For version-aware acceptance, provide file_id.",
)
async def set_key(
    key: DocumentKeyUpdateSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    from datetime import datetime, timezone
    from app.services.project_facts_service import ProjectFactsService

    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )
    if key.name not in AIParsingHandler(db_session).get_keys_by_document_type(document.name.value):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Key '{key.name}' is not allowed for the '{document.name.value}' document",
        )

    document_key_crud = DocumentKeyCRUD(db_session)
    existing_key = document_key_crud.get_document_key(
        name=key.name, document_id=document.id, file_id=key.file_id
    )

    # DD V2 Phase 1.5 server-side override guardrail. The prior guardrail only fired when the
    # client explicitly sent status="overridden"; because the default status is "accepted", a
    # changed baseline-driving value could bypass the rationale requirement entirely. We now
    # resolve the AI-extracted/original value server-side and force the override path (422
    # without a rationale) whenever a baseline-driving value diverges from it — regardless of
    # the client-sent status. A wrong value on these fields silently propagates into
    # expected-production / loss baselines. Reviewer identity is always the authenticated user.
    submitted_value = key.value
    effective_status = key.status or "accepted"

    if is_baseline_driving_field(key.name):
        facts_service = ProjectFactsService(db_session)
        canonical_field = facts_service._resolve_canonical_field(key.name)
        determined, ai_original = facts_service.resolve_ai_original_value(
            document.site_id, canonical_field, key.file_id
        )
        evaluation = evaluate_baseline_override(
            submitted_value=submitted_value,
            ai_determined=determined,
            ai_original=ai_original,
            existing_effective_value=existing_key.effective_value if existing_key else None,
            existing_key_present=existing_key is not None,
            has_rationale=bool(key.override_notes and key.override_notes.strip()),
        )
        if evaluation.requires_rationale:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Changing the baseline-driving field '{key.name}' from the AI-extracted "
                f"value requires a non-empty 'override_notes' rationale.",
            )
        effective_status = evaluation.effective_status

    now = datetime.now(timezone.utc)
    payload = {
        "value": submitted_value,
        "editor_id": current_user.id,
        "file_id": key.file_id,
        "status": effective_status,
    }
    if effective_status == "accepted":
        payload["accepted_by_id"] = current_user.id
        payload["accepted_at"] = now
        # Clear any stale override metadata so (re-)accepting a key drops a prior override.
        payload["override_value"] = None
        payload["overridden_by_id"] = None
        payload["overridden_at"] = None
        payload["override_notes"] = None
    elif effective_status == "overridden":
        payload["override_value"] = key.override_value or submitted_value
        payload["overridden_by_id"] = current_user.id
        payload["overridden_at"] = now
        payload["override_notes"] = key.override_notes

    key_id = existing_key.id if existing_key else None
    key_change_detected = False
    document_key = None

    if not existing_key:
        payload |= {"name": key.name, "document_id": document.id}
        document_key = document_key_crud.create_item(payload)
        key_id = document_key.id
        logger.info(f"Key <{key.name}> has been created for document '{document.id}' file '{key.file_id}'")
        key_change_detected = True
    else:
        if existing_key.value != payload["value"]:
            key_change_detected = True
        document_key_crud.update_by_id(existing_key.id, payload)
        db_session.refresh(existing_key)
        document_key = existing_key
        logger.info(f"Key <{key.name}> has been updated for document '{document.id}' file '{key.file_id}'")
    # track changes of the co-terminus check actuality
    if document.site.co_terminus_check and key_change_detected:
        # based on the co-term config, build dict of agreements and keys used for it
        co_termius_config = CoTerminusHandler(db_session).read()
        source_agreements_names = [
            {"agreement_name": agreement_name, "key_alias": key_alias}
            for key_locations in co_termius_config.values()
            for agreement_name, key_alias in key_locations.items()
        ]

        # group by 'agreement_name'
        co_terminus_sources = defaultdict(list)
        for item in source_agreements_names:
            co_terminus_sources[item["agreement_name"]].append(item["key_alias"])

        # if this key was used for the co-term check - set co-term check as not actual
        if document.name.value in co_terminus_sources and key.name in co_terminus_sources[document.name.value]:
            document.site.co_terminus_check.is_actual = False
            db_session.commit()

    # DD V2 Phase 5B: the legacy DD -> BigQuery characteristics write was removed here.
    # Reviewed/accepted PV Syst values now flow ONLY into project_facts (candidate below),
    # which the V2 expected-baseline path consumes via create-draft-from-facts. DD review
    # and promotion no longer perform any BigQuery I/O.
    if document_key and document_key.file_id and document_key.status in ("accepted", "overridden"):
        try:
            facts_service = ProjectFactsService(db_session)
            # Manual single-key path: no parse run is available here, so no AI evidence
            # is attached. Reviewer identity/rationale come from the document key.
            facts_service.create_candidate_from_document_key(
                document_key,
                document.site_id,
                source_document_type=document.name.value,
            )
            logger.info(f"Created candidate fact for key '{key.name}' file '{key.file_id}'")
        except Exception as e:
            logger.warning(f"Failed to create candidate fact for key '{key.name}': {str(e)}")

    return {"code": status.HTTP_202_ACCEPTED, "message": DocumentMessages.document_key_update_success, "id": key_id}


@documents_router.patch(
    "/{document_id}/keys/{key_id}/poison-pill",
    status_code=status.HTTP_200_OK,
    response_model=DocumentKeyUpdateSuccess,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Toggle poison pill flag on a specific document key. Use key_id=0 with key_name in body to upsert.",
)
async def toggle_poison_pill(
    key_id: int,
    body: DocumentKeyPoisonPillSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    document: Document = Depends(get_authorized_document),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=document.site.company_id,
        project_id=document.site_id,
        db_session=db_session,
        module_key="Diligence",
        action="edit",
    )

    document_key_crud = DocumentKeyCRUD(db_session)

    update_payload = {"is_poison_pill": body.is_poison_pill}
    if body.poison_pill_notes is not None:
        update_payload["poison_pill_notes"] = body.poison_pill_notes

    if key_id == 0:
        if not body.key_name:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "key_name is required when key_id is 0",
            )
        existing_key = document_key_crud.get_document_key(
            name=body.key_name, document_id=document.id, file_id=body.file_id,
        )
        if existing_key:
            document_key_crud.update_by_id(existing_key.id, update_payload)
            result_id = existing_key.id
        else:
            new_key = document_key_crud.create_item({
                "name": body.key_name,
                "document_id": document.id,
                "file_id": body.file_id,
                "editor_id": current_user.id,
                "source": "manual_entry",
                "is_poison_pill": body.is_poison_pill,
                "poison_pill_notes": body.poison_pill_notes,
            })
            result_id = new_key.id
    else:
        existing_key = document_key_crud.get_by_id(key_id)
        if not existing_key or existing_key.document_id != document.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Document key not found")
        document_key_crud.update_by_id(key_id, update_payload)
        result_id = key_id

    return {
        "code": status.HTTP_200_OK,
        "message": "Poison pill flag updated",
        "id": result_id,
    }
