from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

document_sub_sections_mapper = {
    DocumentSections.executive_summary: [],
    DocumentSections.preview: [],
    DocumentSections.stage1: [
        DocumentSections.site_stage1,
        DocumentSections.projectco_lessor,
        DocumentSections.projectco_lessor_parent,
        DocumentSections.incentives_stage1,
        DocumentSections.construction_documents_stage1,
        DocumentSections.utility_operational_documents_stage1,
        DocumentSections.insurance_property_tax_stage1,
        DocumentSections.closing_matters_stage1,
    ],
}

document_name_section_mapper = {
    DocumentSections.executive_summary: [
        SiteDocumentsEnum.executive_summary,
    ],
    DocumentSections.preview: [
        SiteDocumentsEnum.preliminary_ie_review_for_model,
        SiteDocumentsEnum.preliminary_drawings_for_model_electronics,
        SiteDocumentsEnum.preliminary_drawings_for_model_civil,
        SiteDocumentsEnum.seller_initial_pv_syst_full_data_package_for_model,
    ],
    DocumentSections.site_stage1: [
        SiteDocumentsEnum.site_lease,
        SiteDocumentsEnum.title_report_title_commitment,
        SiteDocumentsEnum.evidence_of_application_for_municipal_permits,
        SiteDocumentsEnum.zoning_approval_conditional_use_permit,
        SiteDocumentsEnum.phase_1_esa,
        SiteDocumentsEnum.geotechnical_report,
        SiteDocumentsEnum.alta_survey,
        SiteDocumentsEnum.assignment_of_site_lease_to_projectco_lessor,
        SiteDocumentsEnum.recorded_memorandum_of_site_lease_assignments,
    ],
    DocumentSections.projectco_lessor: [
        SiteDocumentsEnum.articles_of_organization,
        SiteDocumentsEnum.employer_identification_number_w9_or_irs_letter,
        SiteDocumentsEnum.operating_agreements_including_all_amendments_pre_tax_equity,
        SiteDocumentsEnum.certificate_of_good_standing,
        SiteDocumentsEnum.incumbency_certificate_resolutions_proof_of_authority,
        SiteDocumentsEnum.ucc_tax_bankruptcy_judgment_and_pending_litigation_searches,
        SiteDocumentsEnum.ucc_terminations,
    ],
    DocumentSections.projectco_lessor_parent: [
        SiteDocumentsEnum.assignment_of_membership_interests,
        SiteDocumentsEnum.member_officer_resignations,
        SiteDocumentsEnum.seller_certificate_per_3bv,
        SiteDocumentsEnum.firpta,
    ],
    DocumentSections.incentives_stage1: [
        SiteDocumentsEnum.nyserda_grant,
        SiteDocumentsEnum.nyserda_grant_status_portal_screen_shot_due_date,
    ],
    DocumentSections.construction_documents_stage1: [
        SiteDocumentsEnum.ifc_issued_for_construction_stamped_project_drawings,
        SiteDocumentsEnum.building_permit,
        SiteDocumentsEnum.encroachment_driveway_access_permit,
    ],
    DocumentSections.utility_operational_documents_stage1: [
        SiteDocumentsEnum.net_metering_interconnection_application,
        SiteDocumentsEnum.interconnection_agreement_and_amendments,
        SiteDocumentsEnum.cesir,
        SiteDocumentsEnum.nyseg_25_payment,
        SiteDocumentsEnum.nyseg_75_payment,
        SiteDocumentsEnum.nyseg_100_payment,
    ],
    DocumentSections.insurance_property_tax_stage1: [
        SiteDocumentsEnum.epcs_insurance_liability_builders_risk,
        SiteDocumentsEnum.projectcos_liability_insurance,
    ],
    DocumentSections.closing_matters_stage1: [
        SiteDocumentsEnum.payoff_letters,
    ],
}
