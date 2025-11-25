import logging
import re
from typing import Any, Dict

import pandas as pd
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
from tqdm import tqdm

from src.gen_ai.gen_ai import get_llm
from src.pipelines.constants import NOT_PROVIDED_STR, NOT_SUPPORTED_KEY_ITEM
from src.pipelines.term_extraction.pipeline_config import (
    PipelineConfig,
    PVSystPipelineConfig,
)
from src.prompts.prompts import term_summary_prompt_template


logger = logging.getLogger(__name__)


def get_text_after_substring(text: str, substring: str) -> str | None:
    pattern = f"{re.escape(substring)}(.*)"
    match = re.search(pattern, text)
    return match.group(1) if match else None


class TermSummaryPipeline:
    def __init__(self, config: PipelineConfig) -> None:
        """Initialize the TermSummaryPipeline."""
        self.llm: Any = get_llm(model_type=config.model_type)
        self.config = config

        self.chain: LLMChain = self._build_chain()
        try:
            self.short_term_instructions = pd.read_csv(
                config.get_local_terms_path("claude-short-instructions.csv")
            )
        except FileNotFoundError:
            self.short_term_instructions = pd.read_csv(
                config.get_local_terms_path("terms-instructions.csv")
            ).assign(Example="Summarize this text in 3 words.")

    def _build_chain(self) -> LLMChain:
        """Build the Langchain chain."""
        prompt = PromptTemplate.from_template(term_summary_prompt_template())
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain

    def _get_term_summary(self, inputs: Dict[str, str]) -> str:
        """Get the term summary for one predicted term"""
        result: Dict[str, str] = self.chain.invoke(input=inputs)
        return result["text"]

    def run(self, extracted_terms: pd.DataFrame) -> pd.DataFrame:
        """Run the TermSummaryPipeline."""
        logger.info("Running the TermSummaryPipeline")
        term_summaries = []
        for _, row in tqdm(extracted_terms.iterrows(), desc="Getting term summaries"):
            if (
                row["Predicted Legal Terms"]
                and pd.notna(row["Predicted Legal Terms"])
                and not (
                    row["Predicted Legal Terms"].strip()
                    in [
                        '""',
                        "",
                        "Not provided.",
                        "N/A",
                        NOT_PROVIDED_STR,
                        NOT_SUPPORTED_KEY_ITEM,
                    ]
                )
            ):
                short_instructions = self.short_term_instructions[
                    self.short_term_instructions["Key Items"] == row["Key Items"]
                ]["Instructions"].values[0]

                term_summary = self._get_term_summary(
                    inputs={
                        "legal_terms": row["Predicted Legal Terms"],
                        "instructions": short_instructions,
                    }
                ).strip()
                term_summary = self.post_process(term_summary)
                term_summaries.append(term_summary)
            else:
                if "(Y/N)" in row["Key Items"]:
                    term_summaries.append("No.")
                elif row["Predicted Legal Terms"] == NOT_SUPPORTED_KEY_ITEM:
                    term_summaries.append(NOT_SUPPORTED_KEY_ITEM)
                else:
                    term_summaries.append("N/A")

        extracted_terms["Term Summary"] = term_summaries
        logger.info("Running the TermSummaryPipeline completed successfully.")
        return extracted_terms

    @staticmethod
    def post_process(term_summary: str) -> str:
        term_summary = term_summary.strip()
        term_summary_draft = get_text_after_substring(term_summary, "Data retrieved:")
        if term_summary_draft:
            term_summary = term_summary_draft[::]

        term_summary = term_summary.replace("<actual_case>\nData retrieved:\n", "")
        term_summary = term_summary.replace("\n</actual_case>", "")

        return term_summary

    @classmethod
    def from_config(cls, config: PipelineConfig) -> "TermSummaryPipeline":
        """Create a TermSummaryPipeline instance from a PipelineConfig instance."""
        return cls(
            config=config,
        )


class TermSummaryPipelinePVSyst(TermSummaryPipeline):

    def run(self, extracted_terms: pd.DataFrame) -> pd.DataFrame:
        """Run the TermSummaryPipeline."""
        logger.info("Running the TermSummaryPipeline")

        extracted_terms["Term Summary"] = extracted_terms[
            "Predicted Legal Terms"
        ].copy()
        extracted_terms["Predicted Legal Terms"] = pd.read_csv(
            self.config.get_local_terms_path("terms-instructions.csv")
        )["old_names"]
        logger.info("Running the TermSummaryPipeline completed successfully.")
        return extracted_terms


class TermSummaryPipelineFactory:
    """Factory for creating pipelines."""

    @staticmethod
    def create_pipeline(config: PipelineConfig) -> TermSummaryPipeline:
        """Create a pipeline based on the pipeline_name in the config."""
        if config.pipeline_name == PVSystPipelineConfig.pipeline_name:
            logger.info("Creating PVSyst pipeline")
            return TermSummaryPipelinePVSyst.from_config(config)
        else:
            logger.info("Creating default pipeline")
            return TermSummaryPipeline.from_config(config)
