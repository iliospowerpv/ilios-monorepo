from typing import List
from unittest.mock import patch

import pytest

from src.doc_ai.processor import DocAIProcessor


@pytest.fixture
def processor() -> DocAIProcessor:
    """Create a mock DocAIProcessor object"""
    processor = DocAIProcessor(
        project_id="test_project",
        location="test_location",
        processor_id="test_processor",
    )
    return processor


def test_get_processor_name(processor: DocAIProcessor) -> None:
    """
    Test that the get_processor_name method correctly sets the processor name
    """
    with patch.object(
        processor.client, "processor_path", return_value="test_processor_path"
    ):
        assert processor.get_processor_name() == "test_processor_path"


@pytest.mark.parametrize(
    "pages, expected_length",
    [
        ([1, 2, 3], 3),  # Test with multiple pages
        ([1], 1),  # Test with a single page
        ([], 0),  # Test with no pages
        (list(range(1, 101)), 100),  # Test with a large number of pages
        ([1, 2, 2], 3),  # Test with duplicate pages
    ],
)
def test_get_process_options(
    processor: DocAIProcessor, pages: List[int], expected_length: int
) -> None:
    """
    Test that the get_process_options method correctly sets the process options
    """
    process_options = processor.get_process_options(pages=pages)
    assert len(process_options.individual_page_selector.pages) == expected_length
