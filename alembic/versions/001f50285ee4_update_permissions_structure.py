"""update permissions structure

Revision ID: 001f50285ee4
Revises: f68bc038828d
Create Date: 2024-10-11 08:42:35.976080

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.

revision: str = '001f50285ee4'
down_revision: Union[str, None] = 'f68bc038828d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS_UPDATES = [
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
                    "Asset Management": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "Diligence": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "O&M (Production Monitoring)": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    }
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
                    "Asset Management": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "Diligence": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "O&M (Production Monitoring)": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    }
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
                    "Asset Management": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "Diligence": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "O&M (Production Monitoring)": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    }
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
                    "Asset Management": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "Diligence": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "O&M (Production Monitoring)": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    }
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
                    "Asset Management": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "Diligence": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "O&M (Production Monitoring)": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    }
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
                    "Asset Management": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "Diligence": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": true,
                        "import": true,
                        "upload": true,
                        "view": true
                    },
                    "O&M (Production Monitoring)": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    }
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
                    "Asset Management": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "Diligence": {
                        "assign": false,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "O&M (Production Monitoring)": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    }
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
                    "Asset Management": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "Diligence": {
                        "assign": false,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "O&M (Production Monitoring)": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    }
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
                    "Asset Management": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "Diligence": {
                        "assign": false,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "O&M (Production Monitoring)": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    }
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
                    "Asset Management": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "Diligence": {
                        "assign": false,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "O&M (Production Monitoring)": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    }
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
                    "Asset Management": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "Diligence": {
                        "assign": false,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": false,
                        "import": false,
                        "upload": true,
                        "view": true
                    },
                    "O&M (Production Monitoring)": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    }
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
                    "Asset Management": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    },
                    "Diligence": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": true,
                        "import": true,
                        "upload": true,
                        "view": true
                    },
                    "O&M (Production Monitoring)": {
                        "assign": false,
                        "create": false,
                        "delete": false,
                        "download": false,
                        "edit": false,
                        "export": false,
                        "import": false,
                        "upload": false,
                        "view": false
                    }
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
                    "Asset Management": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": true,
                        "import": true,
                        "upload": true,
                        "view": true
                    },
                    "Diligence": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": true,
                        "import": true,
                        "upload": true,
                        "view": true
                    },
                    "O&M (Production Monitoring)": {
                        "assign": true,
                        "create": true,
                        "delete": true,
                        "download": true,
                        "edit": true,
                        "export": true,
                        "import": true,
                        "upload": true,
                        "view": true
                    }
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
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()
    set_permissions(conn, "new_permissions")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    conn = op.get_bind()
    set_permissions(conn, "old_permissions")
    # ### end Alembic commands ###
