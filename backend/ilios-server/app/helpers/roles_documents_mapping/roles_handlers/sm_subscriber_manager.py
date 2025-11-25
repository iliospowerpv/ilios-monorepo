from app.helpers.roles_documents_mapping.base import RoleBasedDocumentConfig
from app.static.roles_documents_mapping.internal_roles_names import InternalRolesNames
from app.static.roles_documents_mapping.sm_subscriber_manager import (
    document_name_section_mapper,
    document_sub_sections_mapper,
)


class SMSubscriberManagerDocuments(RoleBasedDocumentConfig):

    def __init__(self):
        super().__init__(
            document_sub_sections_mapper=document_sub_sections_mapper,
            document_name_section_mapper=document_name_section_mapper,
            role_name=InternalRolesNames.sm_subscriber_manager,
        )
