"""Agreements - the due diligence documents, which are supported by AI to be parsed"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authorization.custom.diligence_overview_page import DiligenceOverviewPagePermissions
from app.helpers.authorization.project_access import get_authorized_document, get_authorized_site
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
    dependencies=[Depends(DiligenceOverviewPagePermissions())],
)
async def get_site_agreements(site: Site = Depends(get_authorized_site), db_session: Session = Depends(get_session)):
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
    dependencies=[Depends(DiligenceOverviewPagePermissions())],
)
async def get_agreement_overview(
    document: Document = Depends(get_authorized_document), db_session: Session = Depends(get_session)
):
    return {"items": combine_user_ai_parsing_results(document=document, db_session=db_session)}
