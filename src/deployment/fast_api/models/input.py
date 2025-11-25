from typing import List, Optional

from pydantic import BaseModel, field_validator


class CoterminousSource(BaseModel):
    document_name: str
    key_item: str
    value: str | int | float


class CoterminousInputItem(BaseModel):
    name: str
    sources: List[CoterminousSource]


class CoterminousInputPayload(BaseModel):
    id: int
    items: List[CoterminousInputItem]


class FileUploadInput(BaseModel):
    file_link: str
    file_id: int
    site_name: str
    site_id: int
    company_name: str
    company_id: int
    agreement_name: str
    document_name: str
    file_name: str
    section_name: str
    subsection_name: Optional[str]

    class Config:
        validate_assignment = True

    @field_validator("subsection_name")
    def set_name(cls, subsection_name: str) -> str:
        return subsection_name or ""
