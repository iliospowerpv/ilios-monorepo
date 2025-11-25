"""set dd permissions for all roles except investor

Revision ID: def2e50eed3f
Revises: d7ecc8264935
Create Date: 2024-12-06 15:15:55.942645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from app.db.migration_utils import set_permissions

revision: str = 'def2e50eed3f'
down_revision: Union[str, None] = 'd7ecc8264935'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS_UPDATES = [
    {
        "name": "Construction Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Project Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Construction Foreman",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Engineer",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Salesperson",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Sales Engineer",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Sales Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Accounting Specialist",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Executive",
        "company_type": "epc_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Project Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Field Technician",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Operations Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Production Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Salesperson",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Sales Engineer",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Sales Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Accounting Specialist",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Executive",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Lender Perm Debt",
        "company_type": "bank",
        "new_permissions": '''{"Asset Management": {"edit": false, "view": false}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Lender Construction",
        "company_type": "bank",
        "new_permissions": '''{"Asset Management": {"edit": false, "view": false}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Appraiser",
        "company_type": "appraiser",
        "new_permissions": '''{"Asset Management": {"edit": false, "view": false}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Engineer",
        "company_type": "engineering_firm",
        "new_permissions": '''{"Asset Management": {"edit": false, "view": false}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Outside Counsel",
        "company_type": "law_firm",
        "new_permissions": '''{"Asset Management": {"edit": false, "view": false}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Subscriber Manager",
        "company_type": "subscriber_manager",
        "new_permissions": '''{"Asset Management": {"edit": false, "view": false}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": false, "view": false}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Insurance Agent",
        "company_type": "insurance_company",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Claims Adjustor",
        "company_type": "insurance_company",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": false, "view": false}}''',
    },
    {
        "name": "Asset Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": false, "view": false}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{"Asset Management": {"edit": true, "view": true}, "Diligence": {"edit": true, "view": true}, "O&M (Production Monitoring)": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}}''',
        "old_permissions": '''{"Diligence": {"edit": false, "view": false}, "Settings Page": {"edit": false, "view": false}, "Asset Management": {"edit": true, "view": true}, "Investor Dashboard": {"edit": false, "view": false}, "Role-based Homepage/Tab": {"edit": false, "view": false}, "O&M (Production Monitoring)": {"edit": true, "view": true}}''',
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    set_permissions(conn, "new_permissions", PERMISSIONS_UPDATES)


def downgrade() -> None:
    conn = op.get_bind()
    set_permissions(conn, "old_permissions", PERMISSIONS_UPDATES)
