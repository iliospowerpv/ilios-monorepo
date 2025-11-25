from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

document_sub_sections_mapper = {
    DocumentSections.executive_summary: [],
    DocumentSections.stage1: [
        DocumentSections.construction_documents_stage1,
        DocumentSections.utility_operational_documents_stage1,
        DocumentSections.insurance_property_tax_stage1,
        DocumentSections.grandfathering_stage1,
    ],
    DocumentSections.stage2: [
        DocumentSections.utility_operational_documents_stage2,
        DocumentSections.substantial_completion_stage2,
    ],
    DocumentSections.stage3: [
        DocumentSections.construction_documents_stage3,
    ],
}

document_name_section_mapper = {
    DocumentSections.executive_summary: [
        SiteDocumentsEnum.executive_summary,
    ],
    DocumentSections.construction_documents_stage1: [
        SiteDocumentsEnum.epc_agreement,
        SiteDocumentsEnum.full_notice_to_proceed,
        SiteDocumentsEnum.epc_production_guaranty,
        SiteDocumentsEnum.project_schedule,
        SiteDocumentsEnum.current_progress_report_construction_complete,
        SiteDocumentsEnum.project_budget_and_draws_requests,
        SiteDocumentsEnum.projectco_invoices,
        SiteDocumentsEnum.draw_1,
        SiteDocumentsEnum.draw_2,
        SiteDocumentsEnum.draw_3,
        SiteDocumentsEnum.draw_4,
        SiteDocumentsEnum.draw_5,
        SiteDocumentsEnum.draw_6,
        SiteDocumentsEnum.draw_7,
        SiteDocumentsEnum.draw_8,
        SiteDocumentsEnum.draw_9,
        SiteDocumentsEnum.draw_10,
        SiteDocumentsEnum.draw_11,
        SiteDocumentsEnum.draw_12,
        SiteDocumentsEnum.draw_13,
        SiteDocumentsEnum.draw_14,
        SiteDocumentsEnum.draw_15,
        SiteDocumentsEnum.draw_16,
        SiteDocumentsEnum.draw_17,
        SiteDocumentsEnum.draw_18,
        SiteDocumentsEnum.draw_19,
        SiteDocumentsEnum.draw_20,
        SiteDocumentsEnum.construction_lien_releases,
        SiteDocumentsEnum.change_order_requests,
    ],
    DocumentSections.utility_operational_documents_stage1: [
        SiteDocumentsEnum.interconnection_agreement_and_amendments,
    ],
    DocumentSections.insurance_property_tax_stage1: [
        SiteDocumentsEnum.epcs_insurance_liability_builders_risk,
    ],
    DocumentSections.grandfathering_stage1: [
        SiteDocumentsEnum.proof_of_start_of_construction,
    ],
    DocumentSections.utility_operational_documents_stage2: [
        SiteDocumentsEnum.permission_to_operate_pto,
        SiteDocumentsEnum.commercial_operation_date_cod,
    ],
    DocumentSections.substantial_completion_stage2: [
        SiteDocumentsEnum.final_construction_lien_releases,
    ],
    DocumentSections.construction_documents_stage3: [
        SiteDocumentsEnum.epc_final_completion_acceptance_report_certificate,
        SiteDocumentsEnum.epc_closeout_documents,
        SiteDocumentsEnum.third_party_review_final_acceptance,
        SiteDocumentsEnum.final_completion_acceptance,
        SiteDocumentsEnum.photos_of_completed_project,
    ],
}
