"""Rollback comments permissions

Revision ID: 2d0b27f6afb8
Revises: 0bffd46a2191
Create Date: 2024-11-08 15:28:30.669670

"""
from typing import Sequence, Union

from alembic import op
from app.db.migration_utils import set_permissions


# revision identifiers, used by Alembic.

revision: str = '2d0b27f6afb8'
down_revision: Union[str, None] = '0bffd46a2191'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS_UPDATES = [
    {
        "name": "Construction Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Project Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Construction Foreman",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Engineer",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Salesperson",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Sales Engineer",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Sales Manager",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Accounting Specialist",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Executive",
        "company_type": "epc_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Project Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Field Technician",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Operations Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Production Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Salesperson",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Sales Engineer",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Sales Manager",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Accounting Specialist",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Executive",
        "company_type": "operation_maintenance_contractor",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Lender Perm Debt",
        "company_type": "bank",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Lender Construction",
        "company_type": "bank",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Appraiser",
        "company_type": "appraiser",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Engineer",
        "company_type": "engineering_firm",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Outside Counsel",
        "company_type": "law_firm",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Investors Counsel",
        "company_type": "law_firm",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Investor",
        "company_type": "investor",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": true, "view": true},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": true, "view": true, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Subscriber Manager",
        "company_type": "subscriber_manager",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Insurance Agent",
        "company_type": "insurance_company",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Claims Adjustor",
        "company_type": "insurance_company",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": true, "view": true, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Asset Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Operations Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Diligence Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Legal Specialist",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Financial Specialist",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Title Specialist",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Developer Liason",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Developer",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": false, "view": false},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": false, "view": false, "comment": false}
        }''',
    },
    {
        "name": "Project Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Marketing Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": false, "view": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": false, "view": false, "comment": false},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": true}
        }''',
    },
    {
        "name": "Salesperson",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Sales Manager",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Accounting Specialist",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": false, "view": false},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": false, "view": false, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Company Admin",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": true, "view": true}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": true, "view": true, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
    {
        "name": "Executive",
        "company_type": "project_site_owner",
        "new_permissions": '''{
            "Asset Management": {"edit": true, "view": true},
            "Diligence": {"edit": true, "view": true},
            "O&M (Production Monitoring)": {"edit": true, "view": true},
            "Investor Dashboard": {"edit": false, "view": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false},
            "Settings Page": {"edit": false, "view": false}
        }''',
        "old_permissions": '''{
            "Diligence": {"edit": true, "view": true, "comment": true},
            "Settings Page": {"edit": false, "view": false, "comment": false},
            "Asset Management": {"edit": true, "view": true, "comment": false},
            "Investor Dashboard": {"edit": false, "view": false, "comment": false},
            "Role-based Homepage/Tab": {"edit": false, "view": false, "comment": false},
            "O&M (Production Monitoring)": {"edit": true, "view": true, "comment": false}
        }''',
    },
]


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()
    set_permissions(conn, "new_permissions", PERMISSIONS_UPDATES)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()
    set_permissions(conn, "old_permissions", PERMISSIONS_UPDATES)
    # ### end Alembic commands ###
