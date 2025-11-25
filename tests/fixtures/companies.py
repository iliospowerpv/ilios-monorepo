import pytest

from app.crud.company import CompanyCRUD
from tests.unit import samples


@pytest.fixture(scope="function", params=[1])
def setup_companies(request, client, system_user_auth_header, db_session):
    """Fixture to create typical companies for multiple tests."""
    companies_to_create = samples.SETUP_COMPANIES[: request.param]
    created_companies = []
    companies_crud = CompanyCRUD(db_session)
    for company in companies_to_create:
        test_company = companies_crud.create_item(company)
        created_companies.append(test_company)

    yield created_companies

    for company in created_companies:
        companies_crud.delete_by_id(company.id)


@pytest.fixture(scope="function")
def company(setup_companies):

    yield setup_companies[0]


@pytest.fixture(scope="function")
def company_id(company):

    yield company.id
