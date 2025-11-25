"""Location of common schemas shared among multiple entities."""

from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

from pydantic import BaseModel, Field


class OrderDirectionEnum(str, Enum):
    """Model of fields enumeration allowed for order/sort direction clause."""

    asc = "asc"  # ascending
    desc = "desc"  # descending


class SuccessUpdateSchema(BaseModel):
    message: str = Field(description="Success message", examples=["Model has been updated"])
    code: int = Field(description="Success status code", examples=[202])


def round_to_scale_2(value: float):
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
