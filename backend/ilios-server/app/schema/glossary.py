"""Response schemas for the expected-production glossary endpoint."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GlossaryTermSchema(BaseModel):
    key: str = Field(
        examples=["expected"],
        description="Stable machine key for FE tooltip lookup (independent of display copy).",
    )
    term: str = Field(examples=["Expected"], description="Human-readable display label.")
    category: str = Field(examples=["Core metrics"], description="Grouping label for the term.")
    definition: str = Field(description="Plain-language definition of the term.")
    applies_to: list[str] = Field(
        default_factory=list,
        examples=[["site", "company", "portfolio"]],
        description="Scopes where the term is meaningful (site/company/portfolio/device).",
    )


class GlossarySchema(BaseModel):
    terms: list[GlossaryTermSchema]
