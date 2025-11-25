import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_text_splitters import CharacterTextSplitter

from src.doc_ai.processor import DocAIProcessor
from src.doc_ai.processors import DOC_AI_PROCESSOR
from src.embeddings.vertex import VertexAIEmbedder
from src.gen_ai.gen_ai import get_llm
from src.pipelines.file_enrichment.prompts import (
    define_risks,
    extract_keywords,
    summarize_document,
)


logger = logging.getLogger(__name__)


class FileEnrichmentPipeline:
    def __init__(self) -> None:
        """Initialize the FileEnrichmentPipeline with base components."""
        self.processor: DocAIProcessor = DocAIProcessor(
            location=os.environ["DOC_AI_LOCATION"],
            project_id=os.environ["PROJECT_ID"],
            processor_id=DOC_AI_PROCESSOR["PROCESSOR"],
        )
        self.chunk_size: int = 6000
        self.text_splitter: CharacterTextSplitter = CharacterTextSplitter(
            separator=".\n",
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_size // 3,
            keep_separator=True,
        )
        self.embedder: VertexAIEmbedder = VertexAIEmbedder()
        self.llm = get_llm(model_type="CLAUDE")

    def run(
        self, metadata: Dict[str, str], file_text: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Metadata should contain the following:
        {
        "file_link": str,
        "file_id": int,
        "site_name": str,
        "site_id": int,
        "company_name": str,
        "company_id": str,
        "agreement_name": str(AgreementType),
        'document_name': str,
        'file_name': str,
        'section_name': str,
        'subsection_name': str
        }
        Method returns list of dictionaries equal to the number of documents/chunks
        in the file.
        """
        if not file_text:
            file_sequence = self.processor.process_documents([metadata["file_link"]])
            file_text = file_sequence.get_all_text()
        document_chunks = self.text_splitter.create_documents([file_text], [metadata])
        doc_chunks: List[str] = [
            self.handle_handle_empty_input(chunk.page_content)
            for chunk in document_chunks
        ]
        logger.info("Creating embeddings")
        embeddings = self.embedder.get_batch_embeddings(doc_chunks)

        llm_chain_keywords, llm_chain_summary, llm_chain_risk = self.prepare_chains()

        logger.info("Running LLM chains for keywords, summaries and risks")
        # calculate keywords, summaries and risks
        keywords_pred = llm_chain_keywords.batch(
            [{"document": chunk} for chunk in doc_chunks]
        )
        summaries: List[str] = llm_chain_summary.batch(  # type: ignore
            [{"document": chunk} for chunk in doc_chunks]
        )
        risks = llm_chain_risk.batch([{"document": chunk} for chunk in doc_chunks])

        logger.info("Parsing chain outputs")
        # parse outputs
        keywords: List[str] = self.validate_llm_output(keywords_pred, key="keywords")
        summaries = self.validate_llm_output(summaries, key="summary")
        risks = self.validate_llm_output(risks, key="risks")

        logger.info("Creating embeddings for summaries")
        summaries = [self.handle_handle_empty_input(summary) for summary in summaries]
        summaries_embeddings = self.embedder.get_batch_embeddings(summaries)

        logger.info("Preparing the final structure")
        # prepare the final structure
        complete_data = [
            {
                "file_id": metadata["file_id"],
                "site_name": metadata["site_name"],
                "site_id": metadata["site_id"],
                "company_name": metadata["company_name"],
                "company_id": metadata["company_id"],
                "agreement_type": metadata["agreement_name"],
                "document": metadata["file_link"],
                "document_name": metadata["document_name"],
                "file_name": metadata["file_name"],
                "section_name": metadata["section_name"],
                "subsection_name": metadata["subsection_name"],
                "embedding": embedding,
                "summary": summary,
                "summary_embedding": summary_embedding,
                "content": doc,
                "keywords": keyword,
                "risks": risk,
                "actual": False,
            }
            for embedding, doc, keyword, risk, summary, summary_embedding in zip(
                embeddings, doc_chunks, keywords, risks, summaries, summaries_embeddings
            )
        ]
        logger.info("Run complete")
        return complete_data

    @staticmethod
    def handle_handle_empty_input(input_text: str) -> str:
        """Handle empty input."""
        if input_text == "":
            return "Empty input"
        return input_text

    def prepare_chains(self) -> Tuple[LLMChain, LLMChain, LLMChain]:
        """Prepare the LLM chains for the FileEnrichmentPipeline."""
        keywords_prompt, summarize_prompt, risk_prompt = self.prepare_prompts()
        llm_chain_keywords = LLMChain(llm=self.llm, prompt=keywords_prompt)
        llm_chain_summary = LLMChain(llm=self.llm, prompt=summarize_prompt)

        llm_chain_risk = LLMChain(llm=self.llm, prompt=risk_prompt)
        return llm_chain_keywords, llm_chain_summary, llm_chain_risk

    @staticmethod
    def prepare_prompts() -> Tuple[PromptTemplate, PromptTemplate, PromptTemplate]:
        """Prepare the prompt templates for the LLM."""
        keywords_prompt = PromptTemplate(
            input_variables=["document"], template=extract_keywords
        )
        summarize_prompt = PromptTemplate(
            input_variables=["document"], template=summarize_document
        )
        risk_prompt = PromptTemplate(
            input_variables=["document"], template=define_risks
        )
        return keywords_prompt, summarize_prompt, risk_prompt

    @staticmethod
    def validate_llm_output(inputs: List[Any], key: str) -> List[Any]:
        """Validate the LLM output."""
        items = []
        for item in inputs:
            try:
                list_of_objects = eval("{" + item["text"].split("{")[-1])[key]
            except Exception as e:
                logger.info(f"Error in parsing the LLM output: {e}")
                if key == "keywords":
                    list_of_objects = []
                else:
                    list_of_objects = ""
            items.append(list_of_objects)
        return items
