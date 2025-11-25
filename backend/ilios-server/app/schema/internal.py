"""Schemas for internal usage, to decrease typo probability"""

from typing import Optional

from pydantic import BaseModel, Field


class ProductionChartData(BaseModel):
    """Describes data model for the BQ production chart (actual and cumulative measurements)"""

    actual_kw: Optional[float] = Field(None, examples=[98.4])
    expected_kw: Optional[float] = Field(None, examples=[130])
    cumulative_actual_kw: Optional[float] = Field(None, examples=[-0.35])
    cumulative_expected_kw: Optional[float] = Field(None, examples=[2])
