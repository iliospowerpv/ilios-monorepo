from typing import List

import pytest

from src.doc_ai.processor import DocAIProcessor


@pytest.fixture
def processor() -> DocAIProcessor:
    return DocAIProcessor(
        project_id="test_project", location="us", processor_id="test_processor"
    )


@pytest.mark.parametrize(
    "page_sizes, page_nums, expected_batches",
    [
        ([10, 10, 10, 10], [0, 1, 2, 3], [[0, 1, 2, 3]]),
        ([10, 10000000, 10000000, 10], [0, 1, 2, 3], [[0, 1], [2, 3]]),
        ([15000000, 6000000, 5, 5], [0, 1, 2, 3], [[0], [1, 2, 3]]),
        ([15000000, 15000000, 15000000, 15000000], [0, 1, 2, 3], [[0], [1], [2], [3]]),
        ([15000000, 5000000, 10, 5], [0, 1, 2, 3], [[0, 1], [2, 3]]),
        (
            [i for i in range(20)],
            [i for i in range(20)],
            [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14], [15, 16, 17, 18, 19]],
        ),
    ],
)
def test_create_batches(
    processor: DocAIProcessor,
    page_sizes: List[int],
    page_nums: List[int],
    expected_batches: List[List[int]],
) -> None:
    batches = list(processor.create_batches(page_sizes, page_nums))
    assert batches == expected_batches
