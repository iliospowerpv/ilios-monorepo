from app.helpers.roles_documents_mapping.base import RoleBasedDocumentConfig
from app.static.roles_documents_mapping.internal_roles_names import InternalRolesNames
from app.static.roles_documents_mapping.om_executive import document_name_section_mapper, document_sub_sections_mapper


class OMExecutiveDocuments(RoleBasedDocumentConfig):

    def __init__(self):
        super().__init__(
            document_sub_sections_mapper=document_sub_sections_mapper,
            document_name_section_mapper=document_name_section_mapper,
            role_name=InternalRolesNames.om_executive,
        )
