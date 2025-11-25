"""Add new user roles

Revision ID: 1635c690e3b5
Revises: 001f50285ee4
Create Date: 2024-10-14 13:14:22.813102

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.crud.role import RoleCRUD
from app.helpers.default_roles_helper import DefaultRolesHelper
from app.static.companies import CompanyTypes

# revision identifiers, used by Alembic.
revision: str = "1635c690e3b5"
down_revision: Union[str, None] = "001f50285ee4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_MVP_ROLES = [  # noqa: ECE001
    (
        "Project Manager",
        CompanyTypes.operation_maintenance_contractor.value,
    ),
    (
        "Field Technician",
        CompanyTypes.operation_maintenance_contractor.value,
    ),
    (
        "Operations Manager",
        CompanyTypes.operation_maintenance_contractor.value,
    ),
    (
        "Production Manager",
        CompanyTypes.operation_maintenance_contractor.value,
    ),
    (
        "Asset Manager",
        CompanyTypes.project_site_owner.value,
    ),
    (
        "Diligence Manager",
        CompanyTypes.project_site_owner.value,
    ),
    (
        "Legal Specialist",
        CompanyTypes.project_site_owner.value,
    ),
    (
        "Financial Specialist",
        CompanyTypes.project_site_owner.value,
    ),
    (
        "Title Specialist",
        CompanyTypes.project_site_owner.value,
    ),
    (
        "Developer Liason",
        CompanyTypes.project_site_owner.value,
    ),
    (
        "Developer",
        CompanyTypes.project_site_owner.value,
    ),
    (
        "Project Manager",
        CompanyTypes.project_site_owner.value,
    ),
    (
        "Executive",
        CompanyTypes.project_site_owner.value,
    ),
]


def upgrade() -> None:
    DefaultRolesHelper(db_session=sa.orm.Session(bind=op.get_bind())).create_default_user_roles()


def downgrade() -> None:
    roles_crud = RoleCRUD(db_session=sa.orm.Session(bind=op.get_bind()))
    existing_roles = {(role.name, role.description): role.id for role in roles_crud.get(skip_pagination=True)}
    for current_role, role_id in existing_roles.items():
        if current_role not in OLD_MVP_ROLES:
            roles_crud.delete_by_id(role_id)
