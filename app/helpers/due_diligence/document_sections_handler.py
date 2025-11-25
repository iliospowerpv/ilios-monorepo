import logging
from collections import defaultdict

from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.roles_documents_mapping.base import RoleBasedDocumentConfig
from app.schema.documents import DocumentSectionSchema, SiteDocumentDetailsSchema, SiteDocumentsSchema
from app.static import DocumentBoardDefaultStatuses

logger = logging.getLogger(__name__)


class DocumentSectionsHandler:

    def __init__(self, site_sections: list, db_session, document_role_config: RoleBasedDocumentConfig = None):
        self.document_role_config = document_role_config

        # filter out site sections by the role config if restrictions should be applied
        if document_role_config:
            site_sections = [
                section for section in site_sections if section.name in document_role_config.role_available_sections
            ]

        # group sections
        self.site_top_level_sections = [section for section in site_sections if section.parent_section_id is None]
        self.parsable_documents = AIParsingHandler(db_session).get_parsable_documents_list()
        # To not call DB each time for related sections - store all site sections in a dict
        self.site_sections_dict = defaultdict(list)
        for section in site_sections:
            self.site_sections_dict[section.parent_section_id].append(section)

    @staticmethod
    def count_section_progress(section_documents=None, related_sections=None):
        completed_tasks_percentage = 0
        if related_sections:
            completed_sub_sections = [
                section for section in related_sections if section["completed_tasks_percentage"] == 100
            ]
            completed_tasks_percentage = (
                round(len(completed_sub_sections) / len(related_sections) * 100) if len(related_sections) > 0 else 0
            )
        if section_documents:
            completed_documents = [
                document
                for document in section_documents
                if document.status == DocumentBoardDefaultStatuses.completed.value
            ]
            completed_tasks_percentage = (
                round(len(completed_documents) / len(section_documents) * 100) if len(section_documents) > 0 else 0
            )
        return completed_tasks_percentage

    def prepare_pydantic_documents_object(self, documents):
        """Crete documents object with Pydantic to add level of field validation"""
        documents_list = [
            SiteDocumentDetailsSchema(
                id=document.id,
                name=document.name,
                files_count=document.files_count,
                assignee=document.assignee,
                status=document.status,
                ai_supported=document.name.value in self.parsable_documents,
            )
            for document in documents
        ]
        return SiteDocumentsSchema(documents=documents_list).model_dump()["documents"]

    def prepare_pydantic_section_object(self, document_section):
        """Crete document section object with Pydantic to add level of field validation"""
        section_documents = self._get_section_documents(document_section)
        document_section = DocumentSectionSchema(
            id=document_section.id,
            name=document_section.name,
            documents_count=len(section_documents),
            completed_tasks_percentage=self.count_section_progress(section_documents),
            documents=self.prepare_pydantic_documents_object(section_documents),
        )
        return document_section.model_dump()

    def _get_section_documents(self, document_section):
        """Filter section documents user role has access to if there are limitations"""
        # return the full documents list if no restriction config provided
        if not self.document_role_config:
            return document_section.documents

        # process the role-based config
        section_documents_by_role = self.document_role_config.document_name_section_mapper.get(document_section.name)
        if not section_documents_by_role:
            # log out warning if this is not the top-level section and nested documents are expected
            if document_section not in self.site_top_level_sections:
                logger.warning(
                    f"Potential role-documents misconfiguration for the role <{self.document_role_config.role_name}> "
                    f"and section <{document_section.name.value}>, returning empty document list"
                )
            # return empty list do not break the calculation
            return []

        # filter out section documents role has access to by the name
        return [document for document in document_section.documents if document.name in section_documents_by_role]

    def build_site_sections_tree(self, section_id: int, site_sections: dict):
        """Recursively builds a tree of all sections and subsections within a site."""
        section_data = site_sections.get(section_id)
        if not section_data:
            return []
        return [
            {
                **self.prepare_pydantic_section_object(related_section),
                "related_sections": self.build_site_sections_tree(related_section.id, site_sections),
            }
            for related_section in section_data
        ]

    def generate_site_documents_response(self):
        """Function to build site section tree using recursion.
        Result includes all sections and subsections with related documents and
        completed_tasks_percentage for each section."""
        documents_response = []
        for top_section in self.site_top_level_sections:
            section_data = {
                **self.prepare_pydantic_section_object(top_section),
                "related_sections": self.build_site_sections_tree(top_section.id, self.site_sections_dict),
            }
            # Update top level section progress based on subsections if at list one subsection exists
            if section_data.get("related_sections"):
                section_data["completed_tasks_percentage"] = self.count_section_progress(
                    related_sections=section_data["related_sections"]
                )
            documents_response.append(section_data)
        return documents_response
