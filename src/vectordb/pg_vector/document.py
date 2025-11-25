from typing import Any, List

from pydantic import BaseModel


class Document(BaseModel):
    """Model of the PGSql document table."""

    file_id: int
    site_name: str
    site_id: int
    company_name: str
    company_id: int
    agreement_type: str
    keywords: List[Any]
    risks: Any
    summary: Any
    summary_embedding: List[float]
    document: str
    content: str
    embedding: List[float]
    actual: bool = False
    document_name: str
    file_name: str
    section_name: str
    subsection_name: str
