"""Unit-tests related helpers"""

import json

from requests import Response
from sqlalchemy.orm import Session

from app.crud.company import CompanyCRUD
from app.crud.user_project import UserProjectCRUD
from app.helpers.authentication import AuthenticationHandler
from app.models.site import Site
from app.models.user import User


def gen_jwt(payload, ttl):
    """Generate JWT for tests"""
    return AuthenticationHandler().create_access_token(payload, ttl)


def clean_up_companies(db_session, company_name):
    companies_crud = CompanyCRUD(db_session)
    db_company = companies_crud.get_by_name(company_name)
    companies_crud.delete_by_id(db_company.id)


def get_company_id(db_session, company_name):
    companies_crud = CompanyCRUD(db_session)
    db_company = companies_crud.get_by_name(company_name)
    return db_company.id


def set_user_site_access(db_session: Session, site: Site, user: User):
    # provide access to the site created by API as well
    UserProjectCRUD(db_session).create_item({"user_id": user.id, "company_id": site.company_id, "site_id": site.id})


def remove_dynamic_fields(data, field_name="id"):
    """Recursively remove field on any level of nesting. By default, removes 'id' field"""
    if isinstance(data, dict):
        if field_name in data:
            del data[field_name]
        for key, value in data.items():
            remove_dynamic_fields(value, field_name)
    elif isinstance(data, list):
        for item in data:
            remove_dynamic_fields(item, field_name)


def create_response(status_code, content_dict):
    response = Response()
    response.status_code = status_code
    response._content = json.dumps(content_dict, indent=2).encode("utf-8")
    return response


def create_file_response(status_code, content_bytes, headers=None):
    response = Response()
    response.status_code = status_code
    response._content = content_bytes
    if headers:
        response.headers = headers
    return response


def get_document_by_name(documents, document_name):
    """Return document by specified name"""
    return [document for document in documents if document.name == document_name][0]
