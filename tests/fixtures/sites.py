import copy
import logging

import pytest

from app.crud.co_terminus_check import CoTerminusCheckCRUD
from app.crud.site import SiteCRUD
from app.crud.site_additional_fields_list import SiteAdditionalFieldListCRUD
from app.helpers.common import get_utc_now
from app.helpers.due_diligence.due_diligence_helper import (
    create_default_site_document_sections,
    generate_default_site_documents,
)
from app.models.session import Session
from app.models.site import SiteStatuses
from tests.unit import samples


def create_default_site_document_sections_for_test(
    site_ids: [] = None,
    db_session: Session = None,
    sub_sections_mapper: list = samples.test_document_sub_sections_mapper,
):
    """Method to monkey patch site default sections creation over API"""
    create_default_site_document_sections(site_ids, db_session, samples.test_document_sub_sections_mapper)


def generate_default_site_documents_for_test(
    site_ids: [] = None, db_session: Session = None, document_mapper: list = samples.test_document_name_section_mapper
):
    """Method to monkey patch site default documents creation over API"""
    return generate_default_site_documents(site_ids, db_session, samples.test_document_name_section_mapper)


@pytest.fixture(scope="function", params=[1])
def sites(request, db_session, company_id):
    """Create several sites via direct DB paste"""
    amount_of_sites = request.param
    created_sites = []
    payload = samples.TEST_SITE_BODY
    payload["company_id"] = company_id
    sites_crud = SiteCRUD(db_session)
    for _ in range(amount_of_sites):
        test_site = sites_crud.create_item(payload)
        created_sites.append(test_site)

    yield created_sites

    for site in created_sites:
        sites_crud.delete_by_id(site.id)


@pytest.fixture(scope="function")
def site(sites):

    yield sites[0]


@pytest.fixture(scope="function")
def site_id(site):

    yield site.id


@pytest.fixture(scope="function", params=[1])
def api_sites(request, db_session, company_id, client, system_user_auth_header, caplog, monkeypatch):
    """Create several sites using API, to have related items populated:
    1. Site board
    2. Site documents
        2.1 Document default board
        2.2 Document default task
    """

    # monkey patch methods for site default documents creation to not create all 300+ documents
    monkeypatch.setattr(
        "app.routers.assets_management.sites.create_default_site_document_sections",
        create_default_site_document_sections_for_test,
    )
    monkeypatch.setattr(
        "app.routers.assets_management.sites.generate_default_site_documents", generate_default_site_documents_for_test
    )
    amount_of_sites = request.param
    created_sites = []
    payload = copy.deepcopy(samples.TEST_SITE_BODY)
    payload.update({"company_id": company_id})
    sites_crud = SiteCRUD(db_session)
    caplog.set_level(logging.INFO)
    # parse site creation logs to populate recently created sites objects
    site_creation_msg = "Created site with id "
    for _ in range(amount_of_sites):
        client.post("/api/sites", json=payload, headers=system_user_auth_header)
        for log in caplog.records:
            if site_creation_msg in log.message:
                created_site_id = log.message.split(site_creation_msg)[-1]
                created_site = sites_crud.get_by_id(created_site_id)
                created_sites.append(created_site)
        caplog.clear()

    yield created_sites

    for site in created_sites:
        sites_crud.delete_by_id(site.id)


@pytest.fixture(scope="function")
def api_site(api_sites):

    yield api_sites[0]


@pytest.fixture(scope="function")
def co_terminus_check(db_session, site_id):
    crud = CoTerminusCheckCRUD(db_session)
    check_item = crud.create_item(
        {
            "site_id": site_id,
            "status": "processing",
            "result": samples.CO_TERM_FIXTURE_RESULTS,
            "start_time": get_utc_now(),
        }
    )
    # use pre saved record_id in case it was already removed by test
    record_id = check_item.id

    yield check_item

    crud.delete_by_id(record_id)


@pytest.fixture(scope="function")
def sites_placed_in_service(db_session, sites):
    """Update sites with placed in service status"""
    sites_extra_crud = SiteAdditionalFieldListCRUD(db_session)
    created_items = []
    for site_ in sites:
        site_addition_details_item = sites_extra_crud.create_item(
            {"site_id": site_.id, "status": SiteStatuses.placed_in_service}
        )
        created_items.append(site_addition_details_item)

    yield

    for site_addition_details_item in created_items:
        sites_extra_crud.delete_by_id(site_addition_details_item.id)
