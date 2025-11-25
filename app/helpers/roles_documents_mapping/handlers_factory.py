from sqlalchemy.orm import Session

from app.crud.role import RoleCRUD
from app.helpers.roles_documents_mapping.roles_handlers import (
    BankLenderConstructionDocuments,
    BankLenderPermDebtDocuments,
    EFEngineerDocuments,
    EPCAccountingSpecialistDocuments,
    EPCConstructionForemanDocuments,
    EPCConstructionManagerDocuments,
    EPCEngineerDocuments,
    EPCExecutiveDocuments,
    EPCMarketingManagerDocuments,
    EPCProjectManagerDocuments,
    EPCSalesEngineerDocuments,
    EPCSalesManagerDocuments,
    EPCSalespersonDocuments,
    ICClaimsAdjustorDocuments,
    ICInsuranceAgentDocuments,
    LFInvestorsCounselDocuments,
    LFOutsideCounselDocuments,
    OMAccountingSpecialistDocuments,
    OMExecutiveDocuments,
    OMFieldTechnicianDocuments,
    OMMarketingManagerDocuments,
    OMOperationsManagerDocuments,
    OMProductionManagerDocuments,
    OMProjectManagerDocuments,
    OMSalesEngineerDocuments,
    OMSalesManagerDocuments,
    OMSalespersonDocuments,
    SMSubscriberManagerDocuments,
)
from app.helpers.roles_documents_mapping.roles_handlers.appr_appraiser import ApprAppraiserDocuments
from app.models.document import Document
from app.static.companies import CompanyTypes
from app.static.roles_documents_mapping.internal_roles_names import (
    EXTERNAL_TO_INTERNAL_ROLES_MAPPING,
    InternalRolesNames,
)


class RoleDocumentsHandlerFactory:
    """Get instance of the document restriction based on the user role"""

    ROLES_HANDLERS = {
        # EPC Contractor
        InternalRolesNames.epc_construction_manager: EPCConstructionManagerDocuments,
        InternalRolesNames.epc_project_manager: EPCProjectManagerDocuments,
        InternalRolesNames.epc_construction_foreman: EPCConstructionForemanDocuments,
        InternalRolesNames.epc_engineer: EPCEngineerDocuments,
        InternalRolesNames.epc_marketing_manager: EPCMarketingManagerDocuments,
        InternalRolesNames.epc_salesperson: EPCSalespersonDocuments,
        InternalRolesNames.epc_sales_engineer: EPCSalesEngineerDocuments,
        InternalRolesNames.epc_sales_manager: EPCSalesManagerDocuments,
        InternalRolesNames.epc_accounting_specialist: EPCAccountingSpecialistDocuments,
        InternalRolesNames.epc_executive: EPCExecutiveDocuments,
        # O&M Contractor
        InternalRolesNames.om_project_manager: OMProjectManagerDocuments,
        InternalRolesNames.om_field_technician: OMFieldTechnicianDocuments,
        InternalRolesNames.om_operations_manager: OMOperationsManagerDocuments,
        InternalRolesNames.om_production_manager: OMProductionManagerDocuments,
        InternalRolesNames.om_marketing_manager: OMMarketingManagerDocuments,
        InternalRolesNames.om_salesperson: OMSalespersonDocuments,
        InternalRolesNames.om_sales_engineer: OMSalesEngineerDocuments,
        InternalRolesNames.om_sales_manager: OMSalesManagerDocuments,
        InternalRolesNames.om_accounting_specialist: OMAccountingSpecialistDocuments,
        InternalRolesNames.om_executive: OMExecutiveDocuments,
        # Bank
        InternalRolesNames.bank_lender_construction: BankLenderConstructionDocuments,
        InternalRolesNames.bank_lender_perm_debt: BankLenderPermDebtDocuments,
        # Appraiser
        InternalRolesNames.appr_appraiser: ApprAppraiserDocuments,
        # Engineering Firm
        InternalRolesNames.ef_engineer: EFEngineerDocuments,
        # Law Firm
        InternalRolesNames.lf_investors_counsel: LFInvestorsCounselDocuments,
        InternalRolesNames.lf_outside_counsel: LFOutsideCounselDocuments,
        # Subscriber Manager
        InternalRolesNames.sm_subscriber_manager: SMSubscriberManagerDocuments,
        # Insurance Company
        InternalRolesNames.ic_insurance_agent: ICInsuranceAgentDocuments,
        InternalRolesNames.ic_claims_adjustor: ICClaimsAdjustorDocuments,
    }

    def get_instance(self, current_user):
        user_role = self._get_internal_role_name(current_user)
        instance = self.ROLES_HANDLERS.get(user_role)
        if instance:
            return instance()

    def _get_internal_role_name(self, current_user):
        """Get internal role name to map the document restrictions"""
        # skip processing if user doesn't have role - it can be treated as a system one
        if not current_user.role:
            return None

        return EXTERNAL_TO_INTERNAL_ROLES_MAPPING.get(self._build_composed_key(current_user))

    @staticmethod
    def _build_composed_key(current_user):
        """Build key as combination of company type and role name for the further mapping"""
        return f"{current_user.role.related_company_type.company_type}.{current_user.role.name}"

    @classmethod
    def get_available_roles_by_document(cls, document: Document, db_session: Session):
        """Opposite logic operation - by the document object, retrieve roles IDs who have access to it"""
        # get attached document details and roles who should have access to it
        roles_with_document_access = []
        for role_name, role_handler in cls.ROLES_HANDLERS.items():
            role_available_documents = role_handler().document_name_section_mapper

            # check if the role has the configuration for the task attached document type
            document_allowed = document.name in role_available_documents.get(document.section.name, [])

            if document_allowed:
                # find role correspondence
                external_role_match = [
                    external_role_name
                    for external_role_name, internal_role_name_role in EXTERNAL_TO_INTERNAL_ROLES_MAPPING.items()
                    if internal_role_name_role == role_name
                ]

                if external_role_match:
                    (role_company_type, user_role_name) = external_role_match[0].split(".")

                    # Note! The DB query uses the company type as a enum, ensure to transform str to enum item
                    roles_with_document_access.append(
                        {"role_name": user_role_name, "company_type": CompanyTypes(role_company_type)}
                    )

        # find IDs of roles who should have access to the document
        output_roles_queryset = RoleCRUD(db_session).get_role_with_document_access(roles_with_document_access)
        output_roles_ids = [row.id for row in output_roles_queryset]
        return output_roles_ids
