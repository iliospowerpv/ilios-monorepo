import pytest

from app.schema.common import calculate_actual_vs_expected
from app.schema.om_site import SiteDashboardActualProductionSection


@pytest.mark.parametrize(
    "actual_performance, expected_performance, test_expected_actual_vs_expected_percent",
    (
        (0, 100, 0),
        (0.4, 100, 0),
        (0.44, 100, 0),
        (0.449, 100, 0),
        (0.45, 100, 0),
        (0.459, 100, 0),
        (0.5, 100, 1),
        (0.9, 100, 1),
        (1, 100, 1),
        (10, 100, 10),
        (50.5, 100, 51),
        (51.5, 100, 52),
        (52.5, 100, 53),
        (73.5, 100, 74),
        (99.5, 100, 100),
        (100.5, 100, 101),
        (103.5, 100, 104),
        (104.5, 100, 105),
        (891, 1000, 89),
        (5050, 10000, 51),
    ),
)
def test_calculate_actual_vs_expected(
    actual_performance, expected_performance, test_expected_actual_vs_expected_percent
):
    # test that percentage is calculated appropriately and rounded half up
    assert (
        calculate_actual_vs_expected(actual_performance, expected_performance)
        == test_expected_actual_vs_expected_percent
    )
