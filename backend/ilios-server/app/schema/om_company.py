"""Company schemas related to the O&M module."""

from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from app.schema.alert import AlertDashboardOverviewSchema, AlertOverviewSchema, OMAlertSchema
from app.schema.common import calculate_actual_vs_expected, round_to_scale_2
from app.schema.company import BaseCompanyPageSchema, CompaniesPageSchema
from app.schema.om_site import CumulativeProductionDetailsBaseSchema, OMSiteCompanyDashboardChartSchema
from app.schema.paginator import BasePaginator


class OMCompaniesPageSchema(CompaniesPageSchema):
    total_actual_kw: float = Field(examples=[5000.0])
    # Optional/None for V2-telemetry companies, which carry actuals only and have
    # no projected/"expected" baseline yet. The frontend uses
    # ``expected_baseline_available`` (not the numeric percent, which collapses to
    # 0) to render "N/A" / "Baseline not available".
    total_expected_kw: Optional[float] = Field(None, examples=[10000.0])
    actual_vs_expected: Optional[int] = Field(None, validate_default=True, examples=[22])
    # Defaults True so any remaining BigQuery path is unchanged; set False by the
    # V2 aggregation path.
    expected_baseline_available: bool = True

    alerts_overview: Optional[Union[AlertOverviewSchema, dict]] = Field(default={"total": 0, "severity": None})

    _round_capacities_to_scale_2 = field_validator("total_actual_kw", "total_expected_kw")(round_to_scale_2)

    @field_validator("actual_vs_expected")
    @classmethod
    def generate_actual_vs_expected(cls, actual_vs_expected, info):  # noqa: U100
        total_actual_kw = info.data.get("total_actual_kw")
        total_expected_kw = info.data.get("total_expected_kw")
        return calculate_actual_vs_expected(total_actual_kw, total_expected_kw)


class OMCompaniesPaginator(BasePaginator):
    """Companies schema along pagination fields included, for the O&M module."""

    items: list[OMCompaniesPageSchema]


class CompanyDashboardActualProductionSection(CumulativeProductionDetailsBaseSchema):
    id: int = Field(examples=[1])
    total_sites: int = Field(examples=[20])
    total_actual_kw: float = Field(examples=[5000.0])
    # Optional/None for V2-telemetry companies (no projected baseline yet).
    total_expected_kw: Optional[float] = Field(None, examples=[10000.0])
    total_system_size_ac: float = Field(examples=[90000.0])
    total_system_size_dc: float = Field(examples=[10000.0])
    actual_vs_expected: Optional[int] = Field(None, validate_default=True, examples=[22])
    # Defaults True (BigQuery path); the V2 aggregation path sets it False so the
    # frontend shows "N/A" / "Baseline not available" for expected fields.
    expected_baseline_available: bool = True

    _round_capacities_to_scale_2 = field_validator(
        "total_actual_kw", "total_expected_kw", "total_system_size_ac", "total_system_size_dc"
    )(round_to_scale_2)

    @field_validator("actual_vs_expected")
    @classmethod
    def generate_actual_vs_expected(cls, actual_vs_expected, info):  # noqa: U100
        total_actual_kw = info.data.get("total_actual_kw")
        total_expected_kw = info.data.get("total_expected_kw")
        return calculate_actual_vs_expected(total_actual_kw, total_expected_kw)


class CompanyDashboardActualVsExpectedSection(BaseModel):
    items: list[OMSiteCompanyDashboardChartSchema]
    # Defaults True (BigQuery path). False for V2 companies: per-site ``expected``
    # is null (no V2 baseline) so the frontend renders the actual-only bubble
    # chart with a no-baseline note instead of misleading zero-expected points.
    expected_baseline_available: bool = True


class CompanyDashboardResponse(BaseCompanyPageSchema):
    """Aggregate all parts of company dashboard under one response"""

    alerts_section: List[OMAlertSchema]
    alerts_summary_section: List[AlertDashboardOverviewSchema]


class CompanyLosesForADaySchema(BaseModel):
    cumulative: float = Field(examples=[753], description="Actual production")
    # Optional/None for V2-telemetry companies: there is no expected baseline, so
    # loss (expected - actual) cannot be computed and is returned as null rather
    # than a misleading 0.
    expected: Optional[float] = Field(None, examples=[602], description="Expected production")
    loss: Optional[float] = Field(
        None,
        examples=[0],
        description="Energy production loses, difference between expected and actual, or 0 if actual is bigger",
    )
    # Defaults True (BigQuery path); the V2 path sets it False so the frontend
    # shows "N/A" / "Baseline not available" for expected and loss.
    expected_baseline_available: bool = True

    _round_capacities_to_scale_2 = field_validator("cumulative", "expected", "loss")(round_to_scale_2)


# Investor Dashboard details


class InvestorDashboardCompanySchema(CompaniesPageSchema):
    total_actual_kw: float = Field(examples=[5000.0])
    # Optional/None for V2-telemetry companies (no projected baseline yet).
    total_expected_kw: Optional[float] = Field(None, examples=[10000.0])
    actual_vs_expected: Optional[int] = Field(None, validate_default=True, examples=[22])
    # Defaults True (BigQuery path); the V2 aggregation path sets it False.
    expected_baseline_available: bool = True

    _round_capacities_to_scale_2 = field_validator("total_actual_kw", "total_expected_kw")(round_to_scale_2)

    @field_validator("actual_vs_expected")
    @classmethod
    def generate_actual_vs_expected(cls, actual_vs_expected, info):  # noqa: U100
        total_actual_kw = info.data.get("total_actual_kw")
        total_expected_kw = info.data.get("total_expected_kw")
        return calculate_actual_vs_expected(total_actual_kw, total_expected_kw)


class InvestorDashboardCompaniesPaginator(BasePaginator):

    items: list[InvestorDashboardCompanySchema]
