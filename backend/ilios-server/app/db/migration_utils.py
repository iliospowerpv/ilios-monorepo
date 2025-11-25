import sqlalchemy as sa


def set_permissions(connection, permissions_key, permission_updates):
    """
    Update permissions based on the role and it's company type.

    Please, specify 'permissions_updates' structure as a list of all roles, where each item is formatted as following:

        {
            "name": <Role name, string>,
            "company_type": <Company type role is attached to, string>,
            "new_permissions": <New permissions dict, json>,
            "old_permissions": <Old permissions dict, json>
        }

    The "new_permissions" and "old_permissions" MUST BE wrapped with triple single quotes, no extra comma at the end,
    this is important for SQL statement which set a json field, boolean values MUST BE defined in lower register.

    The example:

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
            }'''
        }
    """
    for role_obj in permission_updates:
        role_name = role_obj["name"]
        role_company = role_obj["company_type"]
        role_permissions = role_obj[permissions_key]
        statement = f"""UPDATE roles SET permissions = '{role_permissions}'::jsonb FROM company_type_role_mapping
        WHERE company_type_role_mapping.role_id = roles.id
        AND roles.name = '{role_name}' AND company_type_role_mapping.company_type = '{role_company}'"""
        connection.execute(sa.text(statement))
