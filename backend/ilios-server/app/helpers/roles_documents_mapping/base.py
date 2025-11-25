from abc import ABC


class RoleBasedDocumentConfig(ABC):

    def __init__(self, document_sub_sections_mapper, document_name_section_mapper, role_name):
        self.document_sub_sections_mapper = document_sub_sections_mapper
        self.document_name_section_mapper = document_name_section_mapper
        self.role_available_sections = self._generate_sections_list()
        self.role_name = role_name

    def _generate_sections_list(self):
        """Unpack nested sections to have flat section list"""
        return list(self.document_sub_sections_mapper.keys()) + [
            item for value in self.document_sub_sections_mapper.values() for item in value
        ]
