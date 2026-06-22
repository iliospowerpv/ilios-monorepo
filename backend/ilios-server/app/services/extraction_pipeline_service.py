"""
Extraction Pipeline Service

Provides dynamic prompt building and extraction configuration from the registry.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.extraction_registry import (
    ExtractionDocumentTypeCRUD,
    ExtractionSchemaVersionCRUD,
    ExtractionPromptTemplateCRUD,
)
from app.db.base import (
    ExtractionDocumentType,
    ExtractionSchemaVersion,
    ExtractionPromptTemplate,
    CanonicalField,
)

logger = logging.getLogger(__name__)


class ExtractionPipelineService:
    """Service for managing extraction pipeline configuration from registry."""

    def __init__(self, db_session: Session):
        self.db = db_session
        self.doc_type_crud = ExtractionDocumentTypeCRUD(db_session)
        self.schema_crud = ExtractionSchemaVersionCRUD(db_session)
        self.prompt_crud = ExtractionPromptTemplateCRUD(db_session)

    def get_parsable_document_types(self) -> list[str]:
        """Get list of parsable document type names."""
        doc_types = self.doc_type_crud.get_parsable_types()
        return [dt.display_name for dt in doc_types]

    def get_document_type_by_name(self, name: str) -> Optional[ExtractionDocumentType]:
        """Get document type by normalized name."""
        return self.doc_type_crud.get_by_name(name)

    def get_document_type_by_display_name(self, display_name: str) -> Optional[ExtractionDocumentType]:
        """Get document type by display name (case-insensitive)."""
        return self.db.query(ExtractionDocumentType).filter(
            ExtractionDocumentType.display_name.ilike(display_name),
            ExtractionDocumentType.is_active == True,
        ).first()

    def get_active_schema_for_doc_type(self, doc_type_id: int) -> Optional[ExtractionSchemaVersion]:
        """Get the active schema version for a document type."""
        return self.schema_crud.get_active_for_doc_type(doc_type_id)

    def get_active_prompt_for_doc_type(self, doc_type_id: int) -> Optional[ExtractionPromptTemplate]:
        """Get the active prompt template for a document type."""
        return self.prompt_crud.get_active_for_doc_type(doc_type_id)

    def get_schema_fields(self, schema_version_id: int) -> list[CanonicalField]:
        """Get all canonical fields linked to a schema version, ordered by priority."""
        schema = self.schema_crud.get_by_id(schema_version_id)
        if not schema:
            return []

        fields = []
        for link in sorted(schema.fields, key=lambda x: x.extraction_priority or 999):
            if link.canonical_field and link.canonical_field.is_active:
                fields.append(link.canonical_field)
        return fields

    def get_extraction_config(self, document_type_name: str) -> Optional[dict]:
        """
        Get complete extraction configuration for a document type.

        Returns:
            dict with keys: document_type, schema_version, prompt_template, fields
            None if document type not found or not parsable
        """
        doc_type = self.get_document_type_by_name(document_type_name)
        if not doc_type:
            doc_type = self.get_document_type_by_display_name(document_type_name)
        if not doc_type or not doc_type.is_parsable:
            return None

        schema = self.get_active_schema_for_doc_type(doc_type.id)
        prompt = self.get_active_prompt_for_doc_type(doc_type.id)

        if not schema or not prompt:
            logger.warning(f"Missing schema or prompt for document type {doc_type.name}")
            return None

        fields = self.get_schema_fields(schema.id)

        return {
            "document_type": {
                "id": doc_type.id,
                "name": doc_type.name,
                "display_name": doc_type.display_name,
                "category": doc_type.category,
            },
            "schema_version": {
                "id": schema.id,
                "version": schema.version,
            },
            "prompt_template": {
                "id": prompt.id,
                "version": prompt.version,
                "system_prompt": prompt.system_prompt,
                "extraction_prompt": prompt.extraction_prompt,
                "model_name": prompt.model_name,
                "temperature": prompt.temperature,
                "max_tokens": prompt.max_tokens,
            },
            "fields": [
                {
                    "id": f.id,
                    "name": f.name,
                    "display_name": f.display_name,
                    "field_type": f.field_type,
                    # Additive (DD V2 Phase 2): canonical/expected unit hint. May be
                    # None for non-equipment fields. Never used to convert values.
                    "expected_unit": getattr(f, "expected_unit", None),
                }
                for f in fields
            ],
        }

    def build_extraction_prompt(self, document_type_name: str, document_text: str) -> Optional[dict]:
        """
        Build the complete extraction prompt for a document.

        Returns:
            dict with keys: system_prompt, user_prompt, model_config, metadata
            None if configuration not found
        """
        config = self.get_extraction_config(document_type_name)
        if not config:
            return None

        # Build field list with exact field_key for LLM to use
        # Format: "- field_key: Display Name" so LLM knows exact key to return.
        # Additive (DD V2 Phase 2): when a canonical/expected unit is defined for a
        # field, surface it as a hint — "- field_key (W): Display Name" — so the
        # model knows the field's expected unit. This is a hint ONLY; the prompt
        # still instructs the model to preserve the document's raw value and unit
        # and never convert. Fields without an expected_unit are unchanged.
        def _field_line(f: dict) -> str:
            unit = f.get("expected_unit")
            if unit:
                return f"- {f['name']} ({unit}): {f['display_name']}"
            return f"- {f['name']}: {f['display_name']}"

        fields_list = "\n".join(_field_line(f) for f in config["fields"])

        # Use str.replace() instead of .format() to avoid conflicts with JSON braces
        # The prompt template uses {{PLACEHOLDER}} syntax
        extraction_prompt = config["prompt_template"]["extraction_prompt"]
        user_prompt = (
            extraction_prompt
            .replace("{{FIELD_LIST}}", fields_list)
            .replace("{{DOC_TYPE}}", config["document_type"]["display_name"])
            .replace("{{DOCUMENT_TEXT}}", document_text)
        )

        return {
            "system_prompt": config["prompt_template"]["system_prompt"],
            "user_prompt": user_prompt,
            "model_config": {
                "model_name": config["prompt_template"]["model_name"],
                "temperature": config["prompt_template"]["temperature"],
                "max_tokens": config["prompt_template"]["max_tokens"],
            },
            "metadata": {
                "document_type_id": config["document_type"]["id"],
                "schema_version_id": config["schema_version"]["id"],
                "prompt_template_id": config["prompt_template"]["id"],
            },
        }


def get_extraction_pipeline_service(db_session: Session) -> ExtractionPipelineService:
    """Factory function for dependency injection."""
    return ExtractionPipelineService(db_session)
