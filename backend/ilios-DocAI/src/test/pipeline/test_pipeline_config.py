from typing import Any, List
from unittest.mock import patch

import pandas as pd
import pytest

from src.pipelines.term_extraction.pipeline_config import PipelineConfig


# Sample data for mocking
sample_terms_and_definitions = pd.DataFrame(
    {
        "Key Items": ["item1", "item2", "item3"],
        "Definitions": ["definition1", "definition2", "definition3"],
    }
)


@pytest.mark.parametrize(
    "keys, expected_keys",
    [
        ([], ["item1", "item2", "item3"]),  # No keys filter
        (["item1"], ["item1"]),  # Single key filter
        (["item1", "item3"], ["item1", "item3"]),  # Multiple keys filter
        (["item4"], []),  # Non-existent key filter
    ],
)
@patch("src.pipelines.term_extraction.pipeline_config.get_terms_and_definitions")
def test_get_terms_and_definitions(
    mock_get_terms_and_definitions: Any, keys: List[str], expected_keys: List[str]
) -> None:
    # Mock the return value of get_terms_and_definitions
    mock_get_terms_and_definitions.return_value = sample_terms_and_definitions

    # Create an instance of PipelineConfig with the specified keys
    config = PipelineConfig(keys=keys)

    # Call the method
    result = config.get_terms_and_definitions()

    # Check if the result contains the expected keys
    assert list(result["Key Items"]) == expected_keys
