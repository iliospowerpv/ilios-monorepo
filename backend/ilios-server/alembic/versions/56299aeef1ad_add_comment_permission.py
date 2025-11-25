"""add comment permission

Revision ID: 56299aeef1ad
Revises: 1e994d41524e
Create Date: 2024-10-28 12:41:10.602712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from app.static.companies import CompanyTypes

revision: str = '56299aeef1ad'
down_revision: Union[str, None] = '1e994d41524e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# define permissions update changelog
PERMISSIONS_UPDATES = [
    {
        "name": "Construction Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Project Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Construction Foreman",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Engineer",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Salesperson",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Sales Engineer",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Sales Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Accounting Specialist",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Executive",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Project Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true}
        }''',
    },
    {
        "name": "Field Technician",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true}
        }''',
    },
    {
        "name": "Operations Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true}
        }''',
    },
    {
        "name": "Production Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true}
        }''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Salesperson",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Sales Engineer",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Sales Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Accounting Specialist",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Executive",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Lender Perm Debt",
        "company_type": "bank",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Lender Construction",
        "company_type": "bank",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Appraiser",
        "company_type": "appraiser",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Engineer",
        "company_type": "engineering_firm",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Outside Counsel",
        "company_type": "law_firm",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Investors Counsel",
        "company_type": "law_firm",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Investor",
        "company_type": "investor",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": true, "view": true, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": true, "view": true},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Claims Adjustor",
        "company_type": "subscriber_manager",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Insurance Agent",
        "company_type": "insurance_company",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Claims Adjustor",
        "company_type": "insurance_company",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Asset Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true}
        }''',
    },
    {
        "name": "Operations Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Diligence Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Legal Specialist",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Financial Specialist",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Title Specialist",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Developer Liason",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Developer",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Project Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true}
        }''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": true},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Salesperson",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Sales Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Accounting Specialist",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
    },
    {
        "name": "Company Admin",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": true, "view": true, "comment": false}
        }''',
        "old_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": true, "view": true}
        }''',
    },
    {
        "name": "Executive",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Diligence": {"edit": true, "view": true, "comment": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false},
            "Asset Management": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true}
        }''',
    },
]


def set_permissions(connection, permissions_key):
    """Update permissions based on the role and it's company type"""
    for role_obj in PERMISSIONS_UPDATES:
        role_name = role_obj["name"]
        role_company = role_obj["company_type"]
        role_permissions = role_obj[permissions_key]
        statement = f"""UPDATE roles SET permissions = '{role_permissions}'::jsonb FROM company_type_role_mapping
        WHERE company_type_role_mapping.role_id = roles.id
        AND roles.name = '{role_name}' AND company_type_role_mapping.company_type = '{role_company}'"""
        connection.execute(sa.text(statement))


def upgrade() -> None:
    conn = op.get_bind()
    set_permissions(conn, "new_permissions")


def downgrade() -> None:
    conn = op.get_bind()
    set_permissions(conn, "old_permissions")
