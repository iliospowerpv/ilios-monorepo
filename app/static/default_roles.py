"""Default template for the user roles permissions.
Based on the initial request, it should be pre-defined and not manageable, thus it's hardcoded.
In case if you need to make an update, follow the instructions below:
1. Update the default roles structure
2. (Optional) If you add new module (not change existing config) -  update `static/permissions_template.json` as well
3. Generate an alembic migration (it can be empty)
4. Generate a change diff using `dev_scripts/create_permission_updates.py` script
5. Populate the migration, use `35b895480dd9_provide_permission_to_an_asset_for_.py` as the example"""

from app.static.companies import CompanyTypes
from app.static.permissions import PermissionsActions, PermissionsModules

PROJECT_SITE_OWNER_ROLES = [
    # (name, description, list of allowed actions in the following format: module_name.action_name), the company type
    (
        (
            "Asset Manager",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Operations Manager",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Diligence Manager",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Legal Specialist",
            CompanyTypes.project_site_owner.value,
            [
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Financial Specialist",
            CompanyTypes.project_site_owner.value,
            [
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Title Specialist",
            CompanyTypes.project_site_owner.value,
            [
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Developer Liason",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Developer",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Project Manager",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Marketing Manager",
            CompanyTypes.project_site_owner.value,
            [  # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Salesperson",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Sales Manager",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Accounting Specialist",
            CompanyTypes.project_site_owner.value,
            [  # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Company Admin",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Settings
                f"{PermissionsModules.settings}.{PermissionsActions.edit}",
                f"{PermissionsModules.settings}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
    (
        (
            "Executive",
            CompanyTypes.project_site_owner.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.project_site_owner,
    ),
]


INSURANCE_COMPANY_ROLES = [
    (
        (
            "Insurance Agent",
            CompanyTypes.insurance_company.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.insurance_company,
    ),
    (
        (
            "Claims Adjustor",
            CompanyTypes.insurance_company.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.insurance_company,
    ),
]


SUBSCRIBER_MANAGER_ROLES = [
    (
        (
            "Subscriber Manager",
            CompanyTypes.subscriber_manager.value,
            [
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.subscriber_manager,
    ),
]


INVESTOR_ROLES = [
    (
        (
            "Investor",
            CompanyTypes.investor.value,
            [  # investor dashboard
                f"{PermissionsModules.investor_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.investor_dashboard}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.investor,
    ),
]


LAW_FIRM_ROLES = [
    (
        (
            "Outside Counsel",
            CompanyTypes.law_firm.value,
            [  # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.law_firm,
    ),
    (
        (
            "Investors Counsel",
            CompanyTypes.law_firm.value,
            [  # diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.law_firm,
    ),
]


ENGINEERING_FIRM_ROLES = [
    (
        (
            "Engineer",
            CompanyTypes.engineering_firm.value,
            [  # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.engineering_firm,
    ),
]


APPRAISER_ROLES = [
    (
        (
            "Appraiser",
            CompanyTypes.appraiser.value,
            [  # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.appraiser,
    ),
]


BANK_ROLES = [
    (
        (
            "Lender Perm Debt",
            CompanyTypes.bank.value,
            [  # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.bank,
    ),
    (
        (
            "Lender Construction",
            CompanyTypes.bank.value,
            [  # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.bank,
    ),
]


OM_CONTRACTOR_ROLES = [
    # (name, description, list of allowed actions in the following format: module_name.action_name), the company type
    (
        (
            "Project Manager",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Field Technician",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Operations Manager",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Production Manager",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Marketing Manager",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Salesperson",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Sales Engineer",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Sales Manager",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Accounting Specialist",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
    (
        (
            "Executive",
            CompanyTypes.operation_maintenance_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # O&M
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.edit}",
                f"{PermissionsModules.operation_maintenance}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.operation_maintenance_contractor,
    ),
]


EPC_CONTRACTOR_ROLES = [
    (
        (
            "Construction Manager",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Project Manager",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Construction Foreman",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Engineer",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Marketing Manager",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Salesperson",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Sales Engineer",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Sales Manager",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Accounting Specialist",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
    (
        (
            "Executive",
            CompanyTypes.epc_contractor.value,
            [  # assets management
                f"{PermissionsModules.assets_management}.{PermissionsActions.edit}",
                f"{PermissionsModules.assets_management}.{PermissionsActions.view}",
                # Role-based Homepage/Tab
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.edit}",
                f"{PermissionsModules.role_based_dashboard}.{PermissionsActions.view}",
                # Diligence
                f"{PermissionsModules.diligence}.{PermissionsActions.edit}",
                f"{PermissionsModules.diligence}.{PermissionsActions.view}",
                # Reporting
                f"{PermissionsModules.reporting}.{PermissionsActions.edit}",
                f"{PermissionsModules.reporting}.{PermissionsActions.view}",
            ],
        ),
        CompanyTypes.epc_contractor,
    ),
]


MVP_ROLES = [
    *EPC_CONTRACTOR_ROLES,
    *OM_CONTRACTOR_ROLES,
    *BANK_ROLES,
    *APPRAISER_ROLES,
    *ENGINEERING_FIRM_ROLES,
    *LAW_FIRM_ROLES,
    *INVESTOR_ROLES,
    *SUBSCRIBER_MANAGER_ROLES,
    *INSURANCE_COMPANY_ROLES,
    *PROJECT_SITE_OWNER_ROLES,
]
