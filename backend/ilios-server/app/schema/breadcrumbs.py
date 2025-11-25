from typing import Optional

from pydantic import BaseModel, Field


class BreadcrumbsSchema(BaseModel):
    id: int
    name: str = Field(examples=["Ilios"])
    parent_id: Optional[int] = Field(None, examples=[1])
    parent_entity_type: Optional[str] = Field(None, examples=["site"])
