from app.static.default_site_documents_enum import SiteDocumentsEnum

"""
Mapper structure: {"site_card_name": "due_diligence_document_name": [("site_schema_field_name", "document_key_name")]}
"""
SITE_CARDS_FIELD_TO_DD_FIELDS_MAPPER = {
    "site_level_details": {
        SiteDocumentsEnum.as_built_pv_syst_with_full_data_package: [
            ("year_one_expected_production", "Estimated Production (Year 1)")
        ],
        SiteDocumentsEnum.om_agreement: [("degradation_amount", "Degradation")],
    },
    "epc_contractor": {
        SiteDocumentsEnum.epc_agreement: [
            ("provider", "EPC Contractor Name"),
            ("agreement_effective_date", "Effective Date"),
        ],
    },
    "site_lease": {
        SiteDocumentsEnum.site_lease: [
            ("landlord", "Lessor (Landlord) Entity Name"),
            ("tenant", "Lessee (Tenant) Entity Name"),
            ("property_size", "Property Size"),
            ("effective_date", "Effective Date"),
            ("rent_commencement", "Rent Commencement"),
            ("rent_amount", "Rent Amount"),
            ("rent_escalator_effective_date", "Rent Escalator Effective Date"),
            ("initial_term", "Initial Term"),
            ("renewal_terms", "Renewal Terms"),
            ("rent_escalator", "Rent Escalator (Amount)"),
        ],
    },
    "asset_overview": {
        SiteDocumentsEnum.as_built_pv_syst_with_full_data_package: [
            ("module_quantity", "Module Quantity"),
            ("inverter_quantity", "Inverter Quantity"),
            ("project_type", "System Type"),
        ],
    },
    "o_and_m": {
        SiteDocumentsEnum.om_agreement: [
            ("provider", "Provider"),
            ("agreement_effective_date", "Effective Date"),
            ("o_and_m_escalator", "Escalator"),
            ("production_guarantee", "Production Guarantee"),
        ],
    },
    "ownership": {
        SiteDocumentsEnum.permanent_loan_security_agreement: [
            ("guarantor", "Guarantors"),
        ],
    },
    "key_dates": {
        SiteDocumentsEnum.epc_agreement: [
            ("mechanical_completion_date", "Mechanical Completion Date"),
            ("substantial_completion_date", "Substantial Completion Date"),
            ("final_completion_date", "Final Completion Date"),
        ],
    },
    "interconnection": {
        SiteDocumentsEnum.ppa_and_amendments: [
            ("ppa_effective_date", "Effective Date"),
            ("ppa_term", "Term"),
        ],
        SiteDocumentsEnum.interconnection_agreement_and_amendments: [
            ("provider", "Interconnection Utility Company"),
            ("interconnection_agreement_effective_date", "Effective Date"),
        ],
        SiteDocumentsEnum.om_agreement: [
            ("production_guarantee", "Production Guarantee"),
        ],
    },
}
