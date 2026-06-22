"""Extraction Registry Models

This module defines the database models for the Extraction Registry system,
which enables dynamic document type and field management without code changes.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Identity, Integer, String, Text, Boolean, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class ExtractionDocumentType(Base):
    __tablename__ = "extraction_document_types"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False, default="other")
    is_parsable = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    schema_versions = relationship("ExtractionSchemaVersion", back_populates="document_type", cascade="all, delete-orphan")
    prompt_templates = relationship("ExtractionPromptTemplate", back_populates="document_type", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ExtractionDocumentType(id={self.id}, name='{self.name}')>"

    def get_active_schema_version(self):
        for sv in self.schema_versions:
            if sv.is_active:
                return sv
        return None

    def get_active_prompt_template(self):
        for pt in self.prompt_templates:
            if pt.is_active:
                return pt
        return None


class ExtractionSchemaVersion(Base):
    __tablename__ = "extraction_schema_versions"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    document_type_id = Column(Integer, ForeignKey("extraction_document_types.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=utcnow())

    document_type = relationship("ExtractionDocumentType", back_populates="schema_versions")
    created_by = relationship("User", foreign_keys=[created_by_id])
    fields = relationship("ExtractionSchemaVersionField", back_populates="schema_version", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_extraction_schema_versions_doc_type", "document_type_id"),
    )

    def __repr__(self):
        return f"<ExtractionSchemaVersion(id={self.id}, doc_type_id={self.document_type_id}, v={self.version})>"

    def get_ordered_fields(self):
        return sorted(self.fields, key=lambda f: f.extraction_priority)


class ExtractionSchemaVersionField(Base):
    __tablename__ = "extraction_schema_version_fields"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    schema_version_id = Column(Integer, ForeignKey("extraction_schema_versions.id", ondelete="CASCADE"), nullable=False)
    canonical_field_id = Column(Integer, ForeignKey("canonical_fields.id", ondelete="CASCADE"), nullable=False)
    is_required = Column(Boolean, nullable=False, default=False)
    extraction_priority = Column(Integer, nullable=False, default=100)

    schema_version = relationship("ExtractionSchemaVersion", back_populates="fields")
    canonical_field = relationship("CanonicalField")

    __table_args__ = (
        UniqueConstraint("schema_version_id", "canonical_field_id", name="uq_schema_version_field"),
        Index("ix_schema_version_fields_schema", "schema_version_id"),
        Index("ix_schema_version_fields_field", "canonical_field_id"),
    )

    def __repr__(self):
        return f"<ExtractionSchemaVersionField(schema_v={self.schema_version_id}, field={self.canonical_field_id})>"


class ExtractionPromptTemplate(Base):
    __tablename__ = "extraction_prompt_templates"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    document_type_id = Column(Integer, ForeignKey("extraction_document_types.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    system_prompt = Column(Text, nullable=True)
    extraction_prompt = Column(Text, nullable=False)
    model_name = Column(String(100), nullable=False, default="gpt-5.2")
    temperature = Column(Float, nullable=False, default=0.0)
    max_tokens = Column(Integer, nullable=False, default=8000)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=utcnow())

    document_type = relationship("ExtractionDocumentType", back_populates="prompt_templates")
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        Index("ix_extraction_prompt_templates_doc_type", "document_type_id"),
    )

    def __repr__(self):
        return f"<ExtractionPromptTemplate(id={self.id}, doc_type_id={self.document_type_id}, v={self.version})>"


DEFAULT_SYSTEM_PROMPT = """You are a document extraction specialist. Your task is to extract specific data fields from the provided document text. Follow these rules strictly:

1. Extract ONLY the fields listed in the extraction request
2. Return valid JSON matching the exact schema provided
3. For each field, include evidence: page number, relevant text snippet, and anchor text
4. If a field value cannot be found, set value to null but still provide your best guess at where it might appear
5. Be precise with dates, numbers, and currency values
6. Preserve exact wording for text fields when quoting from the document"""

DEFAULT_EXTRACTION_PROMPT = """Extract the following fields from the document:

{{FIELD_LIST}}

Document Type: {{DOC_TYPE}}

=== DOCUMENT TEXT ===
{{DOCUMENT_TEXT}}
=== END DOCUMENT ===

Return a JSON object with the following structure for each field:
{
  "fields": [
    {
      "field_key": "field_name_snake_case",
      "value": "extracted value or null if not found",
      "evidence": {
        "page": 1,
        "snippet": "relevant text from document",
        "anchor_text": "exact matching phrase"
      }
    }
  ]
}

Important:
- field_key must match the snake_case names provided in the field list
- Include ALL fields even if value is null
- Evidence should help a reviewer verify the extraction"""
