from app.helpers.roles_documents_mapping.base import RoleBasedDocumentConfig
from app.static.roles_documents_mapping.ef_engineer import document_name_section_mapper, document_sub_sections_mapper
from app.static.roles_documents_mapping.internal_roles_names import InternalRolesNames


class EFEngineerDocuments(RoleBasedDocumentConfig):

    def __init__(self):
        super().__init__(
            document_sub_sections_mapper=document_sub_sections_mapper,
            document_name_section_mapper=document_name_section_mapper,
            role_name=InternalRolesNames.ef_engineer,
        )
