"""Module to manage due diligence requirement (DDR) objects, previously called documents"""

import logging
from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.document import DocumentCRUD
from app.crud.document_key import DocumentKeyCRUD
from app.crud.document_section import DocumentSectionCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_document, get_authorized_site
from app.helpers.permission_guards import require_module_permission
from app.helpers.bq_data_sync_helper import SiteDDCharacteristicsHandler
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.configs.co_terminus_helper import CoTerminusHandler
from app.helpers.due_diligence.document_key_sync_helper import prepare_keys_sync_payload
from app.helpers.due_diligence.document_sections_handler import DocumentSectionsHandler
from app.helpers.due_diligence.due_diligence_helper import validate_document_section
from app.helpers.roles_documents_mapping.handlers_factory import RoleDocumentsHandlerFactory
from app.helpers.task_tracker import TaskTrackerHandlerFactory
from app.helpers.task_tracker.board_defaults_helper import create_default_board, create_default_document_tasks
from app.models.board import BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.models.document import Document
from app.models.site import Site
from app.schema.documents import (
    CustomDocumentCreationSchema,
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
    UpdateDocumentDescriptionSchema,
    UpdateDocumentDetailsSchema,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, DocumentMessages
from app.static.default_site_documents_enum import SiteDocumentsEnum
from app.static.due_diligence_bq_keys import DueDiligenceBQKeys

logger = logging.getLogger(__name__)
documents_router = APIRouter()


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

    payload = {
        "value": key.value,
        "editor_id": current_user.id,
        "file_id": key.file_id,
        "status": key.status or "accepted",
    }
    if key.status == "accepted":
        payload["accepted_by_id"] = current_user.id
        payload["accepted_at"] = datetime.now(timezone.utc)
    if key.status == "overridden" and key.override_value:
        payload["override_value"] = key.override_value
        payload["overridden_by_id"] = current_user.id
        payload["overridden_at"] = datetime.now(timezone.utc)

    document_key_crud = DocumentKeyCRUD(db_session)
    existing_key = document_key_crud.get_document_key(
        name=key.name, document_id=document.id, file_id=key.file_id
    )
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

    # additional functionality is applied for specific keys of the As-build PV Syst doc:
    # if they were changed need to sync them into BQ
    if (
        document.name == SiteDocumentsEnum.as_built_pv_syst_with_full_data_package
        and key.name in DueDiligenceBQKeys.list()
        and key_change_detected
    ):
        sync_payload = prepare_keys_sync_payload(document_key_crud, document, key)
        SiteDDCharacteristicsHandler(document.site).sync_to_bq(old_record={}, new_record=sync_payload)

    if document_key and document_key.file_id and document_key.status in ("accepted", "overridden"):
        try:
            facts_service = ProjectFactsService(db_session)
            facts_service.create_candidate_from_document_key(document_key, document.site_id)
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
