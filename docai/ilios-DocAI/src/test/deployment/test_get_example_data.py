from typing import Any

import pytest

from src.deployment.cloud_run_job.key_value_extraction.utils import get_example_pp_data
from src.pipelines.constants import AgreementType


@pytest.mark.parametrize(
    "agreement_type, expected_type",
    [
        (AgreementType.SITE_LEASE, list),
        (AgreementType.INTERCONNECTION_AGREEMENT, list),
        (AgreementType.OM_AGREEMENT, list),
        (AgreementType.EPC, list),
        (AgreementType.PPA, list),
    ],
)
def test_get_example_pp_data(agreement_type: AgreementType, expected_type: Any) -> None:
    result = get_example_pp_data(agreement_type)
    assert isinstance(
        result, expected_type
    ), f"Expected result type is not {expected_type}"
    assert len(result) > 0, "The result list is empty"
    assert all(
        isinstance(item, dict) for item in result
    ), "Not all items in the result are dictionaries"
