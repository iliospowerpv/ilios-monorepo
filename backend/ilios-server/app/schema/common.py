"""Location of common schemas shared among multiple entities."""

from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderDirectionEnum(str, Enum):
    """Model of fields enumeration allowed for order/sort direction clause."""

    asc = "asc"  # ascending
    desc = "desc"  # descending


class SuccessUpdateSchema(BaseModel):
    message: str = Field(description="Success message", examples=["Model has been updated"])
    code: int = Field(description="Success status code", examples=[202])


def round_to_scale_2(value: Optional[float]):
    # None-safe: V2 telemetry sites have no expected/projected baseline, so
    # expected_kw/cumulative_expected_kw can legitimately be None. Pydantic v2
    # still runs this validator on None, and round(None, 2) raises TypeError
    # (a 500). Passing None through unchanged keeps the no-baseline contract.
    if value is None:
        return None
    return round(value, 2)


def calculate_actual_vs_expected(actual, expected) -> int | float:
    """Calculate actual/expected ratio"""
    if any((actual == 0, expected == 0, actual is None, expected is None)):
        return 0
    return int((Decimal(actual) / Decimal(expected) * 100).to_integral_value(rounding=ROUND_HALF_UP))


def date_field_validator(date_str: str):
    """Validate date has valid year value"""
    # to be FE-library compatible, otherwise it returns 'Invalid date' on FE
    minimum_year_value = 1900
    if date_str and isinstance(date_str, str):
        date_str_parts = date_str.split("-")
        if date_str_parts:
            year_str = date_str_parts[0]
            if year_str.isnumeric():
                year_value = int(year_str)
                if year_value < minimum_year_value:
                    raise ValueError(f"Year must be {minimum_year_value} or greater")
    return date_str
