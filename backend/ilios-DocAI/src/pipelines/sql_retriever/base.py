import logging
from typing import Any, List

import pandas as pd
from langchain.prompts import Prompt

from src.gen_ai.gen_ai import get_llm
from src.pipelines.mappings import agreements_types_in_db_mapping
from src.pipelines.sql_retriever.prompts import (
    get_agreement_type_prompt,
    get_key_items_prompt,
)
from src.pipelines.sql_retriever.site_documents_enum import (
    DocumentSections,
    SiteDocumentsEnum,
)
from src.pipelines.sql_retriever.sql_connection import SQLConnector
from src.pipelines.sql_retriever.utils import find_closest_match


logger = logging.getLogger(__name__)


class ProjectPreviewRetriever:
    def __init__(self, site_id: int):
        self.site_id = site_id
        self.agreements_types_in_db_mapping = {
            agreement_type.value: value
            for agreement_type, value in agreements_types_in_db_mapping.items()
        }
        self.agreements_types = list(self.agreements_types_in_db_mapping.keys())
        self.sql_connector = SQLConnector()
        self.llm = self.get_llm_agreement_type()

    def get_agreement_type(self, questions: List[str]) -> List[str]:
        """
        Get the agreement type for the questions.
        :param questions:
        :return:
        """
        ans = self.llm.batch([{"question": question} for question in questions])
        ans = [a.content for a in ans]

        # Check that the answer is in the list of agreement types
        answers = []
        for answer in ans:
            answer = answer.replace("AGREEMENT TYPE:", "").strip()
            if answer in self.agreements_types:
                answers.append(answer)
            else:
                answers.append(f"Invalid Agreement Type: {answer}")

        return answers

    @staticmethod
    def get_available_key_items(project_preview_df: pd.DataFrame) -> List[str] | Any:
        """
        Get the available key items from the project preview dataframe
        :param project_preview_df:
        :return:
        """
        return project_preview_df["Key Items"].unique().tolist()

    def get_key_items(self, question: str, available_key_items: List[str]) -> Any:
        """
        Get the key items for the question.
        :param question:
        :param available_key_items:
        :return:
        """
        key_items_prompt = get_key_items_prompt(available_key_items)
        llm_key_items = self.get_llm_key_items(key_items_prompt)
        ans = llm_key_items.invoke({"question": question})
        return ans.content

    def get_llm_agreement_type(self) -> Any:
        """
        Get the LLM model for the agreement type.
        :return:
        """
        prompt = get_agreement_type_prompt(self.agreements_types)
        return prompt | get_llm(model_type="CLAUDE")

    @staticmethod
    def get_llm_key_items(key_items_prompt: Prompt) -> Any:
        """
        Get the LLM model for the key items.
        :param key_items_prompt:
        :return:
        """
        return key_items_prompt | get_llm(model_type="CLAUDE")

    def get_project_preview_data(self, question: str) -> Any:
        """
        Get the agreement type and key items for the question.
        :param question:
        :return:
        """
        agreement_type = self.get_agreement_type([question])[0]
        project_preview = self.get_project_preview_values(agreement_type)
        available_key_items = self.get_available_key_items(project_preview)
        key_items = self.get_key_items(question, available_key_items)
        key_items = key_items.replace("KEY ITEMS:", "").strip()[1:-1].split(",")
        key_items_filtered = self.filter_key_items(available_key_items, key_items)

        return (
            project_preview[project_preview["Key Items"].isin(key_items_filtered)],
            agreement_type,
            project_preview,
            project_preview["Key Items"][
                project_preview["Key Items"].isin(key_items_filtered)
            ].tolist(),
        )

    def get_project_preview_data_by_agreement_type_key_items(
        self, agreement_type: str, key_items: List[str]
    ) -> Any:
        """
        Get the project preview data by agreement type and key items.
        :param agreement_type:
        :param key_items:
        :return:
        """
        project_preview = self.get_project_preview_values(agreement_type)
        available_key_items = self.get_available_key_items(project_preview)
        key_items_filtered = self.filter_key_items(available_key_items, key_items)

        documents = []
        for document_name in project_preview["document_name"].unique():
            document = project_preview[
                project_preview["document_name"] == document_name
            ]
            section_name = (
                document["parent_section_name"].unique()[0]
                if document["parent_section_name"].unique()[0]
                else document["section_name"].unique()[0]
            )
            subsection_name = (
                document["section_name"].unique()[0]
                if document["parent_section_name"].unique()[0]
                else None
            )
            logger.info(f"Subsection Name: {subsection_name}")
            documents.append(
                {
                    "agreement_type": agreement_type,
                    "document_name": SiteDocumentsEnum[document_name].value,
                    "section_name": DocumentSections[section_name].value,
                    "subsection_name": (
                        DocumentSections[subsection_name].value
                        if subsection_name
                        else ""
                    ),
                    "file_name": document["file_name"].unique()[0],
                    "file_path": document["file_path"].unique()[0],
                    "data": (
                        document[document["Key Items"].isin(key_items_filtered)],
                        agreement_type,
                        document,
                        document["Key Items"][
                            document["Key Items"].isin(key_items_filtered)
                        ].tolist(),
                    ),
                }
            )
        return documents

    @staticmethod
    def filter_key_items(
        available_key_items: List[str], key_items: List[str]
    ) -> List[str]:
        key_items_filtered = []
        for key_item in key_items:
            if key_item in available_key_items:
                key_items_filtered.append(key_item)
            else:
                closest_match = find_closest_match(key_item, available_key_items)
                if closest_match:
                    key_items_filtered.append(closest_match)
        return key_items_filtered

    def get_project_preview_values(self, agreement_type: str) -> pd.DataFrame:
        """
        Get a preview of the project data for a given site and document.
        :param agreement_type:
        :return:
        """
        document_names = self.agreements_types_in_db_mapping[agreement_type]
        document_names = (
            (document_names,) if isinstance(document_names, str) else document_names
        )
        return self.sql_connector.get_project_preview_values(
            self.site_id, document_names
        )
