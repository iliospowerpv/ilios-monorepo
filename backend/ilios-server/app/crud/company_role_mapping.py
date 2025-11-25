"""CRUD operations on CompanyTypeRoleMapping model."""

from app.crud.base_crud import BaseCRUD
from app.models.role import CompanyTypeRoleMapping


class CompanyTypeRoleMappingCRUD(BaseCRUD):
    """CRUD operations on CompanyTypeRoleMapping model."""

    def __init__(self, db_session):
        super().__init__(model=CompanyTypeRoleMapping, db_session=db_session)
