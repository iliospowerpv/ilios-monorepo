"""API Schema for paginated responses"""

from typing import Any, List

from pydantic import BaseModel, Field, NonNegativeInt


class BasePaginator(BaseModel):
    skip: NonNegativeInt = Field(examples=[0])
    limit: NonNegativeInt = Field(examples=[10])
    total: NonNegativeInt = Field(examples=[1])
    items: List[Any]
