import logging.config
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.messages.ai import AIMessage
from langchain_core.retrievers import BaseRetriever

from src.doc_ai.file_sequence import FileSequence
from src.doc_ai.processor import DocAIProcessor
from src.gen_ai.gen_ai import get_llm
from src.pipelines.constants import NOT_PROVIDED_STR, NOT_SUPPORTED_KEY_ITEM
from src.pipelines.term_extraction.pipeline_config import (
    LoanAgreementPipelineConfig,
    OperatingAgreementPipelineConfig,
    Phase1ESAConfig,
    PipelineConfig,
    PVSystPipelineConfig,
    SubscriberMgmtPipelineConfig,
)
from src.pipelines.term_extraction.utils import retrieve_section_numbers
from src.prompts.prompts import (
    prompt_template,
    prompt_template_instructions,
    rag_prompt_template,
    rag_prompt_template_pvsyst,
    rag_prompt_template_pvsyst_units,
    retrieve_full_text_of_sections,
    structure_text_of_sections,
)
from src.validation.reviewer.reviewer import Reviewer
from src.vectordb.vectordb import VectorDB


logger = logging.getLogger(__name__)


class Pipeline:
    """Pipeline for building project previews."""

    def __init__(
        self,
        processor_location: str,
        processor_project_id: str,
        processor_id: str,
        terms_and_definitions: pd.DataFrame,
        config: PipelineConfig,
        k: int = 10,
        chunk_size: Optional[int] = None,
        overlap_factor: Optional[int] = 3,
        add_tables: bool = True,
        few_shot: bool = False,
        few_shot_examples: pd.DataFrame = None,
        model_type: str = "CLAUDE",
    ):
        """Initialize the term_extraction."""

        self.processor = DocAIProcessor(
            location=processor_location,
            project_id=processor_project_id,
            processor_id=processor_id,
        )
        self.model_type = model_type
        self.llm = get_llm(model_type=self.model_type)
        chunk_size = chunk_size if chunk_size is not None else 600
        overlap_factor = overlap_factor if overlap_factor is not None else 3
        self.vectordb = VectorDB(
            k=k,
            chunk_size=chunk_size,
            add_tables=add_tables,
            overlap_factor=overlap_factor,
        )
        self.retriever: BaseRetriever
        self.terms_and_definitions_full = terms_and_definitions.copy()
        self.terms_and_definitions = self.terms_and_definitions_preprocess(
            terms_and_definitions
        )
        if few_shot and few_shot_examples is None:
            raise ValueError("few_shot_examples must be provided if few_shot is True")
        self.few_shot = few_shot
        self.few_shot_examples = few_shot_examples
        self.reviewer = Reviewer(model_type=self.model_type)
        self.config = config
        self.postprocess_excluded_keys: List[str] | None = None

        logger.info("Pipeline initialized with the following parameters:")
        logger.info(f"k: {k}")
        logger.info(f"few_shot: {few_shot}")

    @staticmethod
    def terms_and_definitions_preprocess(
        terms_and_definitions: pd.DataFrame,
    ) -> pd.DataFrame:
        col = (
            "Instructions"
            if "Instructions" in terms_and_definitions.columns
            else "Definitions"
        )
        terms_and_instructions = terms_and_definitions[
            ~terms_and_definitions[col].isna()
            & ~terms_and_definitions["Key Items"].isna()
        ]
        return terms_and_instructions

    def get_retriever(self) -> Any:
        """Get the retriever."""
        if self.retriever is None:
            raise ValueError("Retriever has not been built yet.")
        return self.retriever

    def _build_prompt(self, term_definition_row: pd.Series) -> str:
        """
        Builds a prompt for a given term and definition.
        We can change the prompt template here.
        """
        if "Instructions" in term_definition_row:
            term = term_definition_row["Key Items"]
            instructions = term_definition_row["Instructions"]
            prompt = prompt_template_instructions(term, instructions)
            return prompt

        term = term_definition_row["Key Items"]
        definition = term_definition_row["Definitions"]
        if self.few_shot and term in self.few_shot_examples.index:
            examples = [
                example
                for example in self.few_shot_examples.loc[term]
                if not pd.isna(example) and example != NOT_PROVIDED_STR
            ]
        else:
            examples = []

        prompt = prompt_template(term, definition, examples=examples)
        return prompt

    def _build_a_chain(
        self, file_paths: List[str | Path], pages: List[List[int]] | None = None
    ) -> Any:
        """
        Builds a langchain chain for a given file.
        Builds a basic RAG chain for a given file.
        """
        retrieval_qa_chat_prompt = rag_prompt_template()
        logger.info(f"Preparing file for processing: {file_paths}")
        logger.info(f"Processing pages: {pages}")
        try:
            file_sequence: FileSequence = self.processor.process_documents(
                file_paths, pages=pages
            )
        except Exception as e:
            raise ValueError(f"Failed to create FileSequence. Error: {e}")
        self.retriever = self.vectordb.retriever_from_file_sequence(file_sequence)
        combine_docs_chain = create_stuff_documents_chain(
            self.llm, retrieval_qa_chat_prompt
        )

        retrieval_chain = create_retrieval_chain(self.retriever, combine_docs_chain)
        return retrieval_chain

    def build_project_preview(self, file_paths: List[str | Path]) -> pd.DataFrame:
        """
        Main method of the term_extraction. This method builds a project preview for a
        given pdf file.
        :param file_paths: list of files to bundle together like Site Lease plus
            Amendments
        :return:
        """
        logger.info("Build a default chain")
        chain = self._build_a_chain(file_paths)
        logger.info(f"Building project preview for {file_paths}")

        responses = self.build_responses(chain, file_paths)

        logger.info(f"Finished batch processing for {file_paths}")

        project_preview = pd.DataFrame(self.terms_and_definitions["Key Items"])
        project_preview["Predicted Legal Terms"] = responses

        project_preview = self.false_positives_postprocessing(
            project_preview, self.postprocess_excluded_keys
        )

        project_preview["Predicted Legal Terms"] = project_preview[
            "Predicted Legal Terms"
        ].apply(self.remove_triple_backticks)

        project_preview = self.terms_and_definitions_full[["Key Items"]].merge(
            project_preview, on="Key Items", how="left"
        )

        project_preview = self.post_process_on_project_preview_level(project_preview)

        project_preview["Predicted Legal Terms"] = project_preview[
            "Predicted Legal Terms"
        ].fillna(NOT_SUPPORTED_KEY_ITEM)

        return project_preview

    def build_responses(self, chain: Any, file_paths: List[str | Path]) -> List[str]:
        prompts = [
            self._build_prompt(term_definition_row)
            for _, term_definition_row in self.terms_and_definitions.iterrows()
        ]
        logger.info(f"Starting batch processing for {file_paths}")
        responses = chain.batch([{"input": prompt} for prompt in prompts])
        responses = [response["answer"].strip() for response in responses]
        return responses  # type: ignore

    @staticmethod
    def false_positives_postprocessing(
        project_preview: pd.DataFrame, excluded_keys: Optional[List[str]] = None
    ) -> pd.DataFrame:
        if excluded_keys is None:
            excluded_keys = []
        project_preview["Predicted Legal Terms"] = project_preview.apply(
            lambda row: (
                NOT_PROVIDED_STR
                if (
                    ("not provided" in row["Predicted Legal Terms"].lower())
                    or (
                        NOT_PROVIDED_STR.lower() in row["Predicted Legal Terms"].lower()
                    )
                )
                and row["Key Items"] not in excluded_keys
                else row["Predicted Legal Terms"]
            ),
            axis=1,
        )
        return project_preview

    @staticmethod
    def remove_triple_backticks(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        return text

    @classmethod
    def from_config(cls, config: PipelineConfig) -> "Pipeline":
        """Create a Pipeline instance from a PipelineConfig instance."""
        return cls(
            k=config.k,
            chunk_size=config.chunk_size,
            overlap_factor=config.overlap_factor,
            few_shot=config.few_shot,
            terms_and_definitions=config.get_terms_and_definitions(),
            few_shot_examples=config.get_few_shot_examples(),
            add_tables=config.add_tables,
            processor_location=config.processor_location,
            processor_project_id=config.processor_project_id,
            processor_id=config.processor_id,
            model_type=config.model_type,
            config=config,
        )

    @staticmethod
    def post_process_on_project_preview_level(
        project_preview: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Post process the project preview on the project preview level.
        :param project_preview:
        :return:
        """
        return project_preview


class PipelineLoanAgreement(Pipeline):
    """Pipeline for building project previews."""

    process_first_n_pages = 3

    def _build_a_chain_loan_agreement(
        self, file_paths: List[str | Path], pages: List[List[int]] | None = None
    ) -> Any:
        """
        Builds a langchain chain for a given file.
        Builds a basic RAG chain for a given file.
        """
        retrieval_qa_chat_prompt = rag_prompt_template_pvsyst()
        logger.info(f"Preparing file for processing: {file_paths}")
        logger.info(f"Processing pages: {pages}")
        try:
            file_sequence: FileSequence = self.processor.process_documents(
                file_paths, pages=pages
            )
        except Exception as e:
            raise ValueError(f"Failed to create FileSequence. Error: {e}")
        self.retriever = self.vectordb.retriever_from_file_sequence(file_sequence)
        combine_docs_chain = create_stuff_documents_chain(
            self.llm, retrieval_qa_chat_prompt
        )
        retrieval_chain = create_retrieval_chain(self.retriever, combine_docs_chain)
        return retrieval_chain

    def build_responses(self, chain: Any, file_paths: List[str | Path]) -> List[str]:
        """
        Main method of the term_extraction. This method builds a project preview for a
        :param file_paths: list of file paths to process
        :param chain: default chain
        :return:
        """
        chain = self._build_a_chain(file_paths)
        chain_pvsyst = self._build_a_chain_loan_agreement(
            file_paths, pages=[[i for i in range(self.process_first_n_pages)]]
        )
        logger.info(f"Building project preview for {file_paths}")
        terms_and_definitions_pvsyst = self.terms_and_definitions[
            self.terms_and_definitions["use_pvsyst_prompt"].values.astype(bool)
        ]
        terms_and_definitions_other = self.terms_and_definitions[
            ~self.terms_and_definitions["use_pvsyst_prompt"].values.astype(bool)
        ]
        prompts_pvsyst = [
            self._build_prompt(row)
            for _, row in terms_and_definitions_pvsyst.iterrows()
        ]
        prompts_other = [
            self._build_prompt(row) for _, row in terms_and_definitions_other.iterrows()
        ]
        logger.info(f"Starting batch processing for {file_paths}")

        responses_pvsyst = chain_pvsyst.batch(
            [{"input": prompt} for prompt in prompts_pvsyst]
        )
        responses_other = chain.batch([{"input": prompt} for prompt in prompts_other])
        responses = []
        for use_pvsyst_prompt in self.terms_and_definitions[
            "use_pvsyst_prompt"
        ].tolist():
            if use_pvsyst_prompt:
                responses.append(responses_pvsyst.pop(0))
            else:
                responses.append(responses_other.pop(0))

        responses = [response["answer"].strip() for response in responses]

        for i, response in enumerate(responses):
            if pd.notna(self.terms_and_definitions["additional_prompt"].values[i]):
                row = pd.Series(
                    {
                        "Key Items": self.terms_and_definitions["Key Items"].values[i],
                        "Instructions": self.terms_and_definitions[
                            "additional_prompt"
                        ].values[i],
                    }
                )
                ans = chain.invoke({"input": self._build_prompt(row)})["answer"]
                responses[i] = f"{responses[i]}\n{ans}"

        logger.info("Making responses in appropriate format")
        return responses


class PipelinePVSyst(Pipeline):
    """Pipeline for building project previews."""

    def _build_a_chain_pvsyst(self, file_paths: List[str | Path]) -> Any:
        """
        Builds a langchain chain for a given file.
        Builds a basic RAG chain for a given file.
        """
        retrieval_qa_chat_prompt = rag_prompt_template_pvsyst()
        logger.info(f"Preparing file for processing: {file_paths}")
        try:
            file_sequence: FileSequence = self.processor.process_documents(file_paths)
        except Exception as e:
            raise ValueError(f"Failed to create FileSequence. Error: {e}")
        self.retriever = self.vectordb.retriever_from_file_sequence(file_sequence)
        combine_docs_chain = create_stuff_documents_chain(
            self.llm, retrieval_qa_chat_prompt
        )

        retrieval_chain = create_retrieval_chain(self.retriever, combine_docs_chain)
        return retrieval_chain

    def build_responses(self, chain: Any, file_paths: List[str | Path]) -> List[str]:
        """
        Main method of the term_extraction. This method builds a project preview for a
        :param file_paths: list of file paths to process
        :param chain: default chain
        :return:
        """
        chain = self._build_a_chain(file_paths)
        chain_pvsyst = self._build_a_chain_pvsyst(file_paths)
        logger.info(f"Building project preview for {file_paths}")
        terms_and_definitions_pvsyst = self.terms_and_definitions[
            self.terms_and_definitions["use_pvsyst_prompt"].values.astype(bool)
        ]
        terms_and_definitions_other = self.terms_and_definitions[
            ~self.terms_and_definitions["use_pvsyst_prompt"].values.astype(bool)
        ]
        prompts_pvsyst = [
            self._build_prompt(row)
            for _, row in terms_and_definitions_pvsyst.iterrows()
        ]
        prompts_other = [
            self._build_prompt(row) for _, row in terms_and_definitions_other.iterrows()
        ]
        logger.info(f"Starting batch processing for {file_paths}")

        responses_pvsyst = chain_pvsyst.batch(
            [{"input": prompt} for prompt in prompts_pvsyst]
        )
        responses_other = chain.batch([{"input": prompt} for prompt in prompts_other])
        responses = []
        for use_pvsyst_prompt in self.terms_and_definitions[
            "use_pvsyst_prompt"
        ].tolist():
            if use_pvsyst_prompt:
                responses.append(responses_pvsyst.pop(0))
            else:
                responses.append(responses_other.pop(0))

        responses = [response["answer"].strip() for response in responses]
        logger.info("Making responses in appropriate format")
        values = self.make_responses_in_appropriate_format(responses)
        responses = self.add_units_llm(responses, values)
        return responses

    def add_units_llm(self, responses: List[str], values: List[str]) -> List[str]:
        """
        Add units to the responses.
        :param responses:
        :param values:
        :return:
        """

        llm = get_llm(model_type=self.model_type)
        prompt = rag_prompt_template_pvsyst_units()

        prompts_units = [
            prompt.format(text=response, value=value, units=units)
            for response, value, units in zip(
                responses, values, self.terms_and_definitions["unit"].tolist()
            )
            if not pd.isna(units)
        ]

        responses_units_ai_messages: List[AIMessage] = llm.batch(prompts_units)
        responses_units: List[str] = [
            response.content.strip() for response in responses_units_ai_messages  # type: ignore # noqa
        ]

        values_no_units = [
            value
            for value, units in zip(values, self.terms_and_definitions["unit"].tolist())
            if pd.isna(units)
        ]

        responses = []
        for units in self.terms_and_definitions["unit"].tolist():
            if not pd.isna(units):
                responses.append(responses_units.pop(0))
            else:
                responses.append(values_no_units.pop(0))

        return responses

    def make_responses_in_appropriate_format(self, responses: List[str]) -> List[str]:
        """
        Make responses in appropriate format.
        :param responses:
        :return:
        """
        llm = get_llm(model_type=self.model_type)
        short_term_instructions = pd.read_csv(
            self.config.get_local_terms_path("claude-short-instructions.csv")
        )

        prompts = [
            short_term_instruction.format(text=response)
            for short_term_instruction, response in zip(
                short_term_instructions["Instructions"].tolist(), responses
            )
        ]

        responses: List[AIMessage] = llm.batch(prompts)  # type: ignore
        formatted_responses = [
            response.content.strip() for response in responses  # type: ignore
        ]
        return formatted_responses


class PipelinePhaseIESA(Pipeline):
    process_first_n_pages = 5

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.postprocess_excluded_keys = ["RECs (Y/N and $ amount)"]

    def build_responses(self, chain: Any, file_paths: List[str | Path]) -> List[str]:
        """
        Main method of the term_extraction. This method builds a project preview for a
        :param file_paths: list of file paths to process
        :param chain: default chain
        :return:
        """
        logger.info("Build a PHASE 1 CHAIN")
        chain_phase_1_esa = self._build_a_chain(
            file_paths, pages=[[i for i in range(self.process_first_n_pages)]]
        )
        logger.info("Build a SIMPLE CHAIN")

        logger.info(f"Building project preview for {file_paths}")

        # include only first page of the agreement into the processing
        terms_and_definitions_first_page = self.terms_and_definitions[
            self.terms_and_definitions["Use_first_page"].values.astype(bool)
        ]
        # include all the pages of the agreement into the processing
        terms_and_definitions_all_pages = self.terms_and_definitions[
            ~self.terms_and_definitions["Use_first_page"].values.astype(bool)
        ]
        prompts_phase_1 = [
            self._build_prompt(row)
            for _, row in terms_and_definitions_first_page.iterrows()
        ]
        prompts_other = [
            self._build_prompt(row)
            for _, row in terms_and_definitions_all_pages.iterrows()
        ]
        logger.info(f"Starting batch processing for {file_paths}")

        responses_phase_1_esa = chain_phase_1_esa.batch(
            [{"input": prompt} for prompt in prompts_phase_1]
        )
        responses_other = chain.batch([{"input": prompt} for prompt in prompts_other])
        responses = []
        for use_first_page in self.terms_and_definitions["Use_first_page"].tolist():
            if use_first_page:
                responses.append(responses_phase_1_esa.pop(0))
            else:
                responses.append(responses_other.pop(0))

        responses = [response["answer"].strip() for response in responses]
        return responses


class PipelineSubscriberMgmt(Pipeline):
    """Pipeline for building project previews."""

    process_first_n_pages = 3

    def _build_a_chain_subscriber_mgmt(
        self, file_paths: List[str | Path], pages: List[List[int]] | None = None
    ) -> Any:
        """
        Builds a langchain chain for a given file.
        Builds a basic RAG chain for a given file.
        """
        retrieval_qa_chat_prompt = rag_prompt_template_pvsyst()
        logger.info(f"Preparing file for processing: {file_paths}")
        logger.info(f"Processing pages: {pages}")
        try:
            file_sequence: FileSequence = self.processor.process_documents(
                file_paths, pages=pages
            )
        except Exception as e:
            raise ValueError(f"Failed to create FileSequence. Error: {e}")
        self.retriever = self.vectordb.retriever_from_file_sequence(file_sequence)
        combine_docs_chain = create_stuff_documents_chain(
            self.llm, retrieval_qa_chat_prompt
        )
        retrieval_chain = create_retrieval_chain(self.retriever, combine_docs_chain)
        return retrieval_chain

    def _full_text_retrieval(
        self, file_paths: List[str | Path], pages: List[List[int]] | None = None
    ) -> Any:
        """
        Builds a langchain chain for a given file.
        Builds a basic RAG chain for a given file.
        """
        retrieval_qa_chat_prompt = retrieve_full_text_of_sections()
        logger.info(f"Preparing file for processing: {file_paths}")
        logger.info(f"Processing pages: {pages}")
        try:
            file_sequence: FileSequence = self.processor.process_documents(
                file_paths, pages=pages
            )
        except Exception as e:
            raise ValueError(f"Failed to create FileSequence. Error: {e}")
        self.retriever = self.vectordb.retriever_from_file_sequence(file_sequence)
        combine_docs_chain = create_stuff_documents_chain(
            self.llm, retrieval_qa_chat_prompt
        )
        retrieval_chain = create_retrieval_chain(self.retriever, combine_docs_chain)
        return retrieval_chain

    def build_responses(self, chain: Any, file_paths: List[str | Path]) -> List[str]:
        """
        Main method of the term_extraction. This method builds a project preview for a

        Tree possible cases are considered for building a chain:
        1. Use PVSyst prompt and use first n pages
        2. Use PVSyst prompt and do use all pages
        3. Use normal prompt (do not use PVSyst prompt)

        :param file_paths: list of file paths to process
        :param chain: default chain
        :return:
        """
        chain = self._build_a_chain(file_paths)
        chain_pvsyst = self._build_a_chain_subscriber_mgmt(file_paths)
        chain_pvsyst_first_n_pages = self._build_a_chain_subscriber_mgmt(
            file_paths,
            pages=[[i for i in range(self.process_first_n_pages)] for _ in file_paths],
        )

        logger.info(f"Building project preview for {file_paths}")

        terms_and_definitions_pvsyst_first_pages = self.terms_and_definitions[
            (
                self.terms_and_definitions["use_pvsyst_prompt"].values.astype(bool)
                & self.terms_and_definitions["use_first_n_pages"].values.astype(bool)
            )
        ]

        terms_and_definitions_pvsyst = self.terms_and_definitions[
            (
                self.terms_and_definitions["use_pvsyst_prompt"].values.astype(bool)
                & ~self.terms_and_definitions["use_first_n_pages"].values.astype(bool)
            )
        ]
        terms_and_definitions_other = self.terms_and_definitions[
            ~self.terms_and_definitions["use_pvsyst_prompt"].values.astype(bool)
        ]

        prompts_pvsyst_first_pages = [
            row["Instructions"]
            for _, row in terms_and_definitions_pvsyst_first_pages.iterrows()
        ]

        prompts_pvsyst = [
            row["Instructions"] for _, row in terms_and_definitions_pvsyst.iterrows()
        ]
        prompts_other = [
            row["Instructions"] for _, row in terms_and_definitions_other.iterrows()
        ]
        logger.info(f"Starting batch processing for {file_paths}")

        responses_pvsyst_first_pages = chain_pvsyst_first_n_pages.batch(
            [{"input": prompt} for prompt in prompts_pvsyst_first_pages]
        )

        responses_pvsyst = chain_pvsyst.batch(
            [{"input": prompt} for prompt in prompts_pvsyst]
        )
        responses_other = chain.batch([{"input": prompt} for prompt in prompts_other])
        responses = []
        for i in range(self.terms_and_definitions.shape[0]):
            if self.terms_and_definitions["use_pvsyst_prompt"].values.astype(bool)[i]:
                if self.terms_and_definitions["use_first_n_pages"].values.astype(bool)[
                    i
                ]:
                    responses.append(responses_pvsyst_first_pages.pop(0))
                else:
                    responses.append(responses_pvsyst.pop(0))
            else:
                responses.append(responses_other.pop(0))

        responses = [response["answer"].strip() for response in responses]

        chain_for_sections = self._full_text_retrieval(file_paths)
        structure_sections_prompt = structure_text_of_sections()
        for i, response in enumerate(responses):
            if self.terms_and_definitions["check_for_references"].values.astype(bool)[
                i
            ]:

                sections = retrieve_section_numbers(response)
                ans = chain_for_sections.invoke({"input": str(sections)})["answer"]
                clean_ans = self.llm.invoke(
                    structure_sections_prompt.format(input=ans)
                ).content
                responses[i] = f"{responses[i]}\n\n{clean_ans}"

        logger.info("Making responses in appropriate format")
        return responses


class PipelineOperatingAgreement(PipelineSubscriberMgmt):

    process_first_n_pages = 2

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.postprocess_excluded_keys = ["Parties", "Effective Date"]

    def _build_a_chain_operating_agreement(
        self, file_paths: List[str | Path], pages: List[List[int]] | None = None
    ) -> Any:
        """
        Builds a langchain chain for a given file.
        Builds a basic RAG chain for a given file.
        """
        retrieval_qa_chat_prompt = rag_prompt_template()
        logger.info(f"Preparing file for processing: {file_paths}")
        logger.info(f"Processing pages: {pages}")
        try:
            file_sequence: FileSequence = self.processor.process_documents(
                file_paths, pages=pages
            )
        except Exception as e:
            raise ValueError(f"Failed to create FileSequence. Error: {e}")
        self.retriever = self.vectordb.retriever_from_file_sequence(file_sequence)
        combine_docs_chain = create_stuff_documents_chain(
            self.llm, retrieval_qa_chat_prompt
        )
        retrieval_chain = create_retrieval_chain(self.retriever, combine_docs_chain)
        return retrieval_chain

    def build_responses(self, chain: Any, file_paths: List[str | Path]) -> List[str]:
        """
        Main method of the term_extraction. This method builds a project preview for a

        Tree possible cases are considered for building a chain:
        1. Use first n pages
        3. Use all pages

        :param file_paths: list of file paths to process
        :param chain: default chain
        :return:
        """
        chain = self._build_a_chain(file_paths)
        chain_first_n_pages = self._build_a_chain_operating_agreement(
            file_paths,
            pages=[[i for i in range(self.process_first_n_pages)] for _ in file_paths],
        )

        logger.info(f"Building project preview for {file_paths}")

        terms_and_definitions_first_pages = self.terms_and_definitions[
            (self.terms_and_definitions["use_first_n_pages"].values.astype(bool))
        ]

        terms_and_definitions_other = self.terms_and_definitions[
            ~self.terms_and_definitions["use_first_n_pages"].values.astype(bool)
        ]

        prompts_first_n_pages = [
            row["Instructions"]
            for _, row in terms_and_definitions_first_pages.iterrows()
        ]

        prompts_other = [
            row["Instructions"] for _, row in terms_and_definitions_other.iterrows()
        ]
        logger.info(f"Starting batch processing for {file_paths}")

        responses_pvsyst_first_pages = chain_first_n_pages.batch(
            [{"input": prompt} for prompt in prompts_first_n_pages]
        )

        responses_other = chain.batch([{"input": prompt} for prompt in prompts_other])
        responses = []
        for i in range(self.terms_and_definitions.shape[0]):
            if self.terms_and_definitions["use_first_n_pages"].values.astype(bool)[i]:
                responses.append(responses_pvsyst_first_pages.pop(0))
            else:
                responses.append(responses_other.pop(0))

        responses = [response["answer"].strip() for response in responses]

        logger.info("Making responses in appropriate format")
        return responses

    @staticmethod
    def post_process_on_project_preview_level(
        project_preview: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Post process the project preview on the project preview level.
        :param project_preview:
        :return:
        """
        if "Named Manager" in project_preview["Key Items"].values:
            named_manager = project_preview[
                project_preview["Key Items"] == "Named Manager"
            ]["Predicted Legal Terms"].iloc[0]
            parties = project_preview[project_preview["Key Items"] == "Parties"][
                "Predicted Legal Terms"
            ].iloc[0]
            project_preview.loc[
                project_preview["Key Items"] == "Named Manager", "Predicted Legal Terms"
            ] = [named_manager + "\n" + parties]
        return project_preview


class PipelineFactory:
    """Factory for creating pipelines."""

    @staticmethod
    def create_pipeline(config: PipelineConfig) -> Pipeline:
        """Create a pipeline based on the pipeline_name in the config."""
        if config.pipeline_name == LoanAgreementPipelineConfig.pipeline_name:
            logger.info("Creating Loan Agreement pipeline")
            return PipelineLoanAgreement.from_config(config)
        elif config.pipeline_name == PVSystPipelineConfig.pipeline_name:
            logger.info("Creating PVSyst pipeline")
            return PipelinePVSyst.from_config(config)
        elif config.pipeline_name == Phase1ESAConfig.pipeline_name:
            logger.info("Creating Phase I ESA pipeline")
            return PipelinePhaseIESA.from_config(config)
        elif config.pipeline_name == SubscriberMgmtPipelineConfig.pipeline_name:
            logger.info("Creating Subscriber Management pipeline")
            return PipelineSubscriberMgmt.from_config(config)
        elif config.pipeline_name == OperatingAgreementPipelineConfig.pipeline_name:
            logger.info("Creating Operating Agreement pipeline")
            return PipelineOperatingAgreement.from_config(config)
        else:
            logger.info("Creating default pipeline")
            return Pipeline.from_config(config)
