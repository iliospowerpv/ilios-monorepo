from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

document_sub_sections_mapper = {
    DocumentSections.executive_summary: [],
    DocumentSections.preview: [],
    DocumentSections.organization_overview: [],
    DocumentSections.stage1: [
        DocumentSections.construction_documents_stage1,
    ],
    DocumentSections.stage2: [
        DocumentSections.utility_operational_documents_stage2,
        DocumentSections.substantial_completion_stage2,
    ],
}

document_name_section_mapper = {
    DocumentSections.executive_summary: [
        SiteDocumentsEnum.executive_summary,
    ],
    DocumentSections.construction_documents_stage1: [
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
    DocumentSections.utility_operational_documents_stage2: [
        SiteDocumentsEnum.permission_to_operate_pto,
        SiteDocumentsEnum.commercial_operation_date_cod,
    ],
    DocumentSections.substantial_completion_stage2: [
        SiteDocumentsEnum.as_built_project_drawings,
    ],
}
