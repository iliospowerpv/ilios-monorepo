from enum import Enum

from app.static.companies import CompanyTypes


class InternalRolesNames(Enum):
    epc_construction_manager = "Construction Manager (EPC)"
    epc_project_manager = "Project Manager (EPC)"
    epc_construction_foreman = "Construction Foreman (EPC)"
    epc_engineer = "Engineer (EPC)"
    epc_marketing_manager = "Marketing Manager (EPC)"
    epc_salesperson = "Salesperson (EPC)"
    epc_sales_engineer = "Sales Engineer (EPC)"
    epc_sales_manager = "Sales Manager (EPC)"
    epc_accounting_specialist = "Accounting Specialist (EPC)"
    epc_executive = "Executive (EPC)"
    om_project_manager = "Project Manager (O&M)"
    om_field_technician = "Field Technician (O&M)"
    om_operations_manager = "Operations Manager (O&M)"
    om_production_manager = "Production Manager (O&M)"
    om_marketing_manager = "Marketing Manager (O&M)"
    om_salesperson = "Salesperson (O&M)"
    om_sales_engineer = "Sales Engineer (O&M)"
    om_sales_manager = "Sales Manager (O&M)"
    om_accounting_specialist = "Accounting Specialist (O&M)"
    om_executive = "Executive (O&M)"
    bank_lender_construction = "Lender Construction (Bank)"
    bank_lender_perm_debt = "Lender Perm Debt (Bank)"
    # Appraiser
    appr_appraiser = "Appraiser (Appraiser)"
    # Engineering Firm
    ef_engineer = "Engineer (Engineering Firm)"
    # Law Firm
    lf_investors_counsel = "Investors Counsel (Law Firm)"
    lf_outside_counsel = "Outside Counsel (Law Firm)"
    # Subscriber Manager
    sm_subscriber_manager = "Subscriber Manager (Subscriber Manager)"
    # Insurance Company
    ic_insurance_agent = "Insurance Agent (Insurance Company)"
    ic_claims_adjustor = "Claims Adjustor (Insurance Company)"


"""
Use composed key of company type and role name to map to the corresponding internal roles. For example:
    <company_type>.<role_name>: <internal role name>
"""
EXTERNAL_TO_INTERNAL_ROLES_MAPPING = {
    # EPC Contractor
    f"{CompanyTypes.epc_contractor.value}.Construction Manager": InternalRolesNames.epc_construction_manager,
    f"{CompanyTypes.epc_contractor.value}.Project Manager": InternalRolesNames.epc_project_manager,
    f"{CompanyTypes.epc_contractor.value}.Construction Foreman": InternalRolesNames.epc_construction_foreman,
    f"{CompanyTypes.epc_contractor.value}.Engineer": InternalRolesNames.epc_engineer,
    f"{CompanyTypes.epc_contractor.value}.Marketing Manager": InternalRolesNames.epc_marketing_manager,
    f"{CompanyTypes.epc_contractor.value}.Salesperson": InternalRolesNames.epc_salesperson,
    f"{CompanyTypes.epc_contractor.value}.Sales Engineer": InternalRolesNames.epc_sales_engineer,
    f"{CompanyTypes.epc_contractor.value}.Sales Manager": InternalRolesNames.epc_sales_manager,
    f"{CompanyTypes.epc_contractor.value}.Accounting Specialist": InternalRolesNames.epc_accounting_specialist,
    f"{CompanyTypes.epc_contractor.value}.Executive": InternalRolesNames.epc_executive,
    # O&M Contractor
    f"{CompanyTypes.operation_maintenance_contractor.value}.Project Manager": InternalRolesNames.om_project_manager,
    f"{CompanyTypes.operation_maintenance_contractor.value}.Field Technician": InternalRolesNames.om_field_technician,
    f"{CompanyTypes.operation_maintenance_contractor.value}.Operations Manager": InternalRolesNames.om_operations_manager,  # noqa: E501
    f"{CompanyTypes.operation_maintenance_contractor.value}.Production Manager": InternalRolesNames.om_production_manager,  # noqa: E501
    f"{CompanyTypes.operation_maintenance_contractor.value}.Marketing Manager": InternalRolesNames.om_marketing_manager,
    f"{CompanyTypes.operation_maintenance_contractor.value}.Salesperson": InternalRolesNames.om_salesperson,
    f"{CompanyTypes.operation_maintenance_contractor.value}.Sales Engineer": InternalRolesNames.om_sales_engineer,
    f"{CompanyTypes.operation_maintenance_contractor.value}.Sales Manager": InternalRolesNames.om_sales_manager,
    f"{CompanyTypes.operation_maintenance_contractor.value}.Accounting Specialist": InternalRolesNames.om_accounting_specialist,  # noqa: E501
    f"{CompanyTypes.operation_maintenance_contractor.value}.Executive": InternalRolesNames.om_executive,
    # Bank
    f"{CompanyTypes.bank.value}.Lender Construction": InternalRolesNames.bank_lender_construction,
    f"{CompanyTypes.bank.value}.Lender Perm Debt": InternalRolesNames.bank_lender_perm_debt,
    # Appraiser
    f"{CompanyTypes.appraiser.value}.Appraiser": InternalRolesNames.appr_appraiser,
    # Engineering Firm
    f"{CompanyTypes.engineering_firm.value}.Engineer": InternalRolesNames.ef_engineer,
    # Law Firm
    f"{CompanyTypes.law_firm.value}.Investors Counsel": InternalRolesNames.lf_investors_counsel,
    f"{CompanyTypes.law_firm.value}.Outside Counsel": InternalRolesNames.lf_outside_counsel,
    # Subscriber Manager
    f"{CompanyTypes.subscriber_manager.value}.Subscriber Manager": InternalRolesNames.sm_subscriber_manager,
    # Insurance Company
    f"{CompanyTypes.insurance_company.value}.Insurance Agent": InternalRolesNames.ic_insurance_agent,
    f"{CompanyTypes.insurance_company.value}.Claims Adjustor": InternalRolesNames.ic_claims_adjustor,
}
