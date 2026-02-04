"""Agreements - the due diligence documents, which are supported by AI to be parsed"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_document, get_authorized_site
from app.helpers.permission_guards import require_module_permission
from app.schema.user import CurrentUserSchema
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.files.file_helper import combine_user_ai_parsing_results
from app.models.document import Document
from app.models.site import Site
from app.schema.documents import DocumentKeysListSchema, ParsableDocumentsListSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
agreements_router = APIRouter()


@agreements_router.get(
    "/",
    response_model=ParsableDocumentsListSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Return list of site agreements (documents) available for AI parsing",
)
async def get_site_agreements(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
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
    ai_parsable_documents = AIParsingHandler(db_session).get_parsable_documents_list()
    parsable_documents = []
    for document in site.documents:
        if document.name.value in ai_parsable_documents:
            # build document name together with the section name
            document_name = (
                f"{document.name.value} — {document.section.name.value}" if document.section else document.name.value
            )
            parsable_documents.append(
                {
                    "id": document.id,
                    "name": document_name,
                }
            )
    # Add sorting A-Z including section name
    parsable_documents = sorted(parsable_documents, key=lambda d: d["name"])
    return {"items": parsable_documents}


@agreements_router.get(
    "/{document_id}/overview",
    response_model=DocumentKeysListSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_agreement_overview(
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
    # Find the primary file (is_actual) or the file with the latest completed parsing result
    primary_file = None
    for f in document.files:
        if f.deleted:
            continue
        if f.is_actual:
            primary_file = f
            break
    # If no is_actual file, find the one with the latest completed parsing
    if not primary_file:
        from app.models.file import FileParsingStatuses
        for f in document.files:
            if f.deleted:
                continue
            if f.latest_ai_result and f.latest_ai_result.status == FileParsingStatuses.completed:
                primary_file = f
                break
    return {"items": combine_user_ai_parsing_results(document=document, db_session=db_session, due_diligence_file=primary_file)}
