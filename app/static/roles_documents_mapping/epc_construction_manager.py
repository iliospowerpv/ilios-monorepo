from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

document_sub_sections_mapper = {
    DocumentSections.executive_summary: [],
    DocumentSections.preview: [],
    DocumentSections.stage1: [
        DocumentSections.site_stage1,
        DocumentSections.construction_documents_stage1,
        DocumentSections.utility_operational_documents_stage1,
    ],
    DocumentSections.stage3: [
        DocumentSections.construction_documents_stage3,
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
    ],
    DocumentSections.construction_documents_stage1: [
        SiteDocumentsEnum.epc_agreement,
        SiteDocumentsEnum.full_notice_to_proceed,
        SiteDocumentsEnum.epc_production_guaranty,
        SiteDocumentsEnum.ifc_issued_for_construction_pv_syst_first_buyer_pv_syst_report,
        SiteDocumentsEnum.ifc_issued_for_construction_stamped_project_drawings,
        SiteDocumentsEnum.project_schedule,
        SiteDocumentsEnum.current_progress_report_construction_complete,
        SiteDocumentsEnum.epc_permit_studies_letter,
        SiteDocumentsEnum.local_building_permits_electrical_construction_etc,
        SiteDocumentsEnum.electrical_permit,
        SiteDocumentsEnum.application_for_electrical_permit,
        SiteDocumentsEnum.building_permit,
        SiteDocumentsEnum.application_for_building_permit,
        SiteDocumentsEnum.encroachment_driveway_access_permit,
        SiteDocumentsEnum.application_for_encroachment_driveway_access_permit,
        SiteDocumentsEnum.change_order_requests,
        SiteDocumentsEnum.monitoring_system_and_das,
        SiteDocumentsEnum.ofe_owner_furnished_equipment_proof_of_procurement,
        SiteDocumentsEnum.module_specs,
        SiteDocumentsEnum.module_warranty,
        SiteDocumentsEnum.module_warranty_backup_documents,
        SiteDocumentsEnum.racking_specs,
        SiteDocumentsEnum.racking_warranty,
        SiteDocumentsEnum.fully_executed_racking_warranty,
        SiteDocumentsEnum.racking_warranty_backup_documents,
        SiteDocumentsEnum.inverter_specs,
        SiteDocumentsEnum.inverter_warranty,
        SiteDocumentsEnum.inverter_warranty_backup_documents,
        SiteDocumentsEnum.transformer_specs,
        SiteDocumentsEnum.transformer_warranty,
        SiteDocumentsEnum.transformer_warranty_backup_documents,
        SiteDocumentsEnum.storage_specs,
        SiteDocumentsEnum.battery_specs,
        SiteDocumentsEnum.storage_warranty,
        SiteDocumentsEnum.storage_warranty_backup_documents,
        SiteDocumentsEnum.battery_warranty,
        SiteDocumentsEnum.battery_warranty_backup_documents,
    ],
    DocumentSections.utility_operational_documents_stage1: [
        SiteDocumentsEnum.interconnection_agreement_and_amendments,
    ],
    DocumentSections.construction_documents_stage3: [
        SiteDocumentsEnum.photos_of_completed_project,
    ],
}
