from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

document_sub_sections_mapper = {
    DocumentSections.executive_summary: [],
    DocumentSections.stage1: [
        DocumentSections.construction_documents_stage1,
        DocumentSections.utility_operational_documents_stage1,
    ],
    DocumentSections.stage2: [
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
        SiteDocumentsEnum.net_metering_interconnection_application,
        SiteDocumentsEnum.interconnection_agreement_and_amendments,
    ],
    DocumentSections.substantial_completion_stage2: [
        SiteDocumentsEnum.as_built_pv_syst_with_full_data_package,
        SiteDocumentsEnum.seller_independent_pv_syst_report,
        SiteDocumentsEnum.as_built_project_drawings,
        SiteDocumentsEnum.epc_substantial_completion_report_certificate,
        SiteDocumentsEnum.independent_engineer_report,
        SiteDocumentsEnum.placed_in_service_pis_letter,
    ],
    DocumentSections.construction_documents_stage3: [
        SiteDocumentsEnum.final_completion_acceptance,
        SiteDocumentsEnum.photos_of_completed_project,
    ],
}
