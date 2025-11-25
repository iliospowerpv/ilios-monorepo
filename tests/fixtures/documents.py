import pytest

import tests.unit.samples as samples
from app.crud.document import DocumentCRUD
from app.crud.document_key import DocumentKeyCRUD
from app.crud.document_section import DocumentSectionCRUD
from app.helpers.due_diligence.due_diligence_helper import (
    create_default_site_document_sections,
    generate_default_site_documents,
)
from app.static.default_site_documents_enum import SiteDocumentsEnum
from tests.utils import get_document_by_name


@pytest.fixture(scope="function")
def document_sections(db_session, site):
    create_default_site_document_sections([site.id], db_session, samples.test_document_sub_sections_mapper)
    document_sections = DocumentSectionCRUD(db_session).get_site_sections(site.id)

    yield document_sections


@pytest.fixture(scope="function")
def document_section(document_sections):
    yield document_sections[0]


@pytest.fixture(scope="function")
def documents(db_session, site, document_sections):
    DocumentCRUD(db_session).create_items(
        generate_default_site_documents([site.id], db_session, samples.test_document_name_section_mapper)
    )

    yield site.documents

    # Documents are deleted by cascade after


@pytest.fixture(scope="function")
def document(documents):
    # always return executive summary document
    yield get_document_by_name(documents, SiteDocumentsEnum.executive_summary)


@pytest.fixture(scope="function")
def site_lease_document(documents):
    yield get_document_by_name(documents, SiteDocumentsEnum.site_lease)


@pytest.fixture(scope="function")
def site_lease_document_key(site_lease_document, db_session):
    key_obj = DocumentKeyCRUD(db_session).create_item(
        {"document_id": site_lease_document.id, "name": "Lessor (Landlord) Entity Name", "value": "RE-company"}
    )
    yield key_obj


@pytest.fixture(scope="function")
def all_site_documents(db_session, sites):
    """Create documents for all sites we create with the <sites> fixture"""
    for site in sites:
        create_default_site_document_sections([site.id], db_session)
        DocumentCRUD(db_session).create_items(generate_default_site_documents([site.id], db_session))

    # there is no need to return documents since they are available as a backref property of the site object
    yield


@pytest.fixture(scope="function")
def ppa_agreement_ai_fields(db_session, all_site_documents, site):
    ppa_and_amendments = get_document_by_name(site.documents, SiteDocumentsEnum.ppa_and_amendments)
    DocumentKeyCRUD(db_session).create_items(
        [
            {"document_id": ppa_and_amendments.id, "name": "Effective Date", "value": "12/14/2022"},
            {"document_id": ppa_and_amendments.id, "name": "Term", "value": "20"},
        ]
    )

    yield
