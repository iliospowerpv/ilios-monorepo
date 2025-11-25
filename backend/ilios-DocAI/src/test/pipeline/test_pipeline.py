import os
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.doc_ai.processors import DOC_AI_PROCESSOR
from src.pipelines.term_extraction.pipeline import Pipeline
from src.pipelines.term_extraction.pipeline_config import PipelineConfig


terms_and_definitions = pd.DataFrame(
    {"Key Items": ["term1", "term2"], "Definitions": ["def1", "def2"]}
)


@pytest.fixture
def pipeline() -> Pipeline:
    """Create a mock Pipeline object."""
    pipeline = Pipeline(
        os.environ["DOC_AI_LOCATION"],
        os.environ["PROJECT_ID"],
        DOC_AI_PROCESSOR["PROCESSOR"],
        terms_and_definitions,
        PipelineConfig(),
    )
    return pipeline


def test_init() -> None:
    """Test the initialization of the Pipeline class."""
    pipeline = Pipeline(
        os.environ["DOC_AI_LOCATION"],
        os.environ["PROJECT_ID"],
        DOC_AI_PROCESSOR["PROCESSOR"],
        terms_and_definitions,
        PipelineConfig(),
    )
    assert pipeline.terms_and_definitions.equals(terms_and_definitions)


@patch("src.pipelines.term_extraction.pipeline.prompt_template")
def test__build_prompt(mock_prompt_template: Mock, pipeline: Pipeline) -> None:
    """Test that the _build_prompt method returns a prompt."""
    term_definition_row = pd.Series(
        {"Key Items": "term1", "Definitions": "def1", "example1": "example1"}
    )
    mock_prompt_template.return_value = "prompt"
    prompt = pipeline._build_prompt(term_definition_row)
    assert prompt == "prompt"


@patch("src.pipelines.term_extraction.pipeline.create_retrieval_chain")
@patch("src.pipelines.term_extraction.pipeline.DocAIProcessor")
def test__build_a_chain(
    mock_DocAIProcessor: Mock,
    mock_create_retrieval_chain: Mock,
    pipeline: Pipeline,
) -> None:
    mock_file = Mock()
    mock_file.get_all_text.return_value = "text"
    mock_file.is_processed = True
    mock_file.get_tables.return_value = [
        pd.DataFrame({"a": [1, 2], "b": [3, 4]}),
        pd.DataFrame({"c": [5, 6], "d": [7, 8]}),
    ]
    mock_file.get_form_fields.return_value = [{"a": "b"}, {"c": "d"}]

    mock_DocAIProcessor.process_documents.return_value = mock_file
    pipeline.processor = mock_DocAIProcessor

    mock_chain = Mock()
    mock_chain.with_config.return_value = mock_chain
    mock_create_retrieval_chain.return_value = mock_chain

    chain = pipeline._build_a_chain(["file_path"])
    assert chain == mock_chain
