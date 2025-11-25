from typing import Dict, List

import numpy as np
import pytest

from src.deployment.fast_api.models.input import CoterminousInputItem, CoterminousSource
from src.deployment.fast_api.models.output import (
    ComparisonStatus,
    CoterminousOutputItem,
)
from src.pipelines.co_terminus_check.base import CoTerminusCheck


@pytest.fixture
def co_terminus_check() -> CoTerminusCheck:
    """Create a mock CoTerminusCheck object."""
    return CoTerminusCheck()


def test_init(co_terminus_check: CoTerminusCheck) -> None:
    """Test the initialization of the CoTerminusCheck class."""
    assert isinstance(co_terminus_check, CoTerminusCheck)


@pytest.mark.parametrize(
    "results, expected",
    [
        (
            {"Test": True},
            [CoterminousOutputItem(status=ComparisonStatus.EQUAL, name="Test")],
        ),
        (
            {"Test": False},
            [CoterminousOutputItem(status=ComparisonStatus.NOT_EQUAL, name="Test")],
        ),
    ],
)
def test_map_to_output(
    co_terminus_check: CoTerminusCheck,
    results: Dict[str, bool],
    expected: List[CoterminousOutputItem],
) -> None:
    """Test the map_to_output method."""
    result = co_terminus_check.map_to_output(results)
    assert result == expected


@pytest.mark.parametrize(
    "results, expected",
    [
        (
            [{"result": True, "name": "Test"}, {"result": True, "name": "Test"}],
            {"Test": True},
        ),
        (
            [{"result": True, "name": "Test"}, {"result": False, "name": "Test"}],
            {"Test": False},
        ),
        (
            [
                {"result": True, "name": "Test"},
                {"result": False, "name": "Test"},
                {"result": True, "name": "Test_2"},
            ],
            {"Test": False, "Test_2": True},
        ),
    ],
)
def test_group_responses(
    co_terminus_check: CoTerminusCheck,
    results: List[Dict[str, str | bool]],
    expected: Dict[str, bool],
) -> None:
    """Test the group_responses method."""
    result = co_terminus_check.group_responses(results)
    assert result == expected


@pytest.mark.parametrize(
    "results, expected",
    [
        (["true", "false"], [True, False]),
        (["True", "False"], [True, False]),
        (["TRUE", "FALSE"], [True, False]),
        (["* True", "invalid"], [np.nan, np.nan]),
        (["invalid"], [np.nan]),
    ],
)
def test_check_response(
    co_terminus_check: CoTerminusCheck, results: List[str], expected: List[bool]
) -> None:
    """Test the __check_response method."""
    result = co_terminus_check._CoTerminusCheck__check_response(results)  # type: ignore
    assert result == expected


@pytest.mark.parametrize(
    "items, expected",
    [
        (
            [
                CoterminousInputItem(
                    name="Test",
                    sources=[
                        CoterminousSource(
                            document_name="Doc1", key_item="Item1", value="Value1"
                        ),
                        CoterminousSource(
                            document_name="Doc2", key_item="Item2", value="Value2"
                        ),
                        CoterminousSource(
                            document_name="Doc3", key_item="Item3", value="Value3"
                        ),
                        CoterminousSource(
                            document_name="Doc4", key_item="Item4", value="Value4"
                        ),
                    ],
                )
            ],
            [
                {
                    "name": "Test",
                    "document_type_1": "Doc1",
                    "key_item_1": "Item1",
                    "value_1": "Value1",
                    "document_type_2": "Doc2",
                    "key_item_2": "Item2",
                    "value_2": "Value2",
                },
                {
                    "name": "Test",
                    "document_type_1": "Doc1",
                    "key_item_1": "Item1",
                    "value_1": "Value1",
                    "document_type_2": "Doc3",
                    "key_item_2": "Item3",
                    "value_2": "Value3",
                },
                {
                    "name": "Test",
                    "document_type_1": "Doc1",
                    "key_item_1": "Item1",
                    "value_1": "Value1",
                    "document_type_2": "Doc4",
                    "key_item_2": "Item4",
                    "value_2": "Value4",
                },
            ],
        ),
        (
            [
                CoterminousInputItem(
                    name="Test",
                    sources=[
                        CoterminousSource(
                            document_name="Doc1", key_item="Item1", value="Value1"
                        ),
                        CoterminousSource(
                            document_name="Doc2", key_item="Item2", value="Value2"
                        ),
                        CoterminousSource(
                            document_name="Doc3", key_item="Item3", value="Value3"
                        ),
                    ],
                )
            ],
            [
                {
                    "name": "Test",
                    "document_type_1": "Doc1",
                    "key_item_1": "Item1",
                    "value_1": "Value1",
                    "document_type_2": "Doc2",
                    "key_item_2": "Item2",
                    "value_2": "Value2",
                },
                {
                    "name": "Test",
                    "document_type_1": "Doc1",
                    "key_item_1": "Item1",
                    "value_1": "Value1",
                    "document_type_2": "Doc3",
                    "key_item_2": "Item3",
                    "value_2": "Value3",
                },
            ],
        ),
    ],
)
def test_generate_comparison_pairs(
    co_terminus_check: CoTerminusCheck,
    items: List[CoterminousInputItem],
    expected: List[Dict[str, str]],
) -> None:
    """Test the generate_comparison_pairs method."""
    result = co_terminus_check.generate_comparison_pairs(items)
    assert result == expected
