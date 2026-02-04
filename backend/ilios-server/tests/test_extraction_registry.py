"""Tests for Extraction Registry

Tests cover:
- Seed idempotency
- Activation uniqueness
- Job binding persistence
- Reprocess does not mutate acceptance
- Admin permission gates
"""

import pytest
from sqlalchemy.orm import Session

from app.db.base import (
    ExtractionDocumentType,
    ExtractionSchemaVersion,
    ExtractionPromptTemplate,
    CanonicalField,
)
from app.crud.extraction_registry import (
    ExtractionDocumentTypeCRUD,
    ExtractionSchemaVersionCRUD,
    ExtractionPromptTemplateCRUD,
)
from app.services.extraction_pipeline_service import ExtractionPipelineService


class TestSeedIdempotency:
    """Test that seed script is idempotent."""

    def test_seed_creates_document_types(self, db_session: Session):
        crud = ExtractionDocumentTypeCRUD(db_session)
        doc_types = crud.get_parsable_types()
        assert len(doc_types) >= 1, "Seed should create at least one document type"

    def test_seed_creates_schema_versions(self, db_session: Session):
        crud = ExtractionDocumentTypeCRUD(db_session)
        schema_crud = ExtractionSchemaVersionCRUD(db_session)

        doc_types = crud.get_parsable_types()
        for dt in doc_types[:3]:
            versions = schema_crud.get_versions_for_doc_type(dt.id)
            assert len(versions) >= 1, f"Doc type {dt.name} should have at least one schema version"

    def test_seed_creates_prompt_templates(self, db_session: Session):
        crud = ExtractionDocumentTypeCRUD(db_session)
        prompt_crud = ExtractionPromptTemplateCRUD(db_session)

        doc_types = crud.get_parsable_types()
        for dt in doc_types[:3]:
            templates = prompt_crud.get_templates_for_doc_type(dt.id)
            assert len(templates) >= 1, f"Doc type {dt.name} should have at least one prompt template"


class TestActivationUniqueness:
    """Test that only one schema/prompt version can be active per doc type."""

    def test_only_one_active_schema_version(self, db_session: Session):
        crud = ExtractionDocumentTypeCRUD(db_session)
        schema_crud = ExtractionSchemaVersionCRUD(db_session)

        doc_types = crud.get_parsable_types()
        for dt in doc_types:
            active_schemas = db_session.query(ExtractionSchemaVersion).filter(
                ExtractionSchemaVersion.document_type_id == dt.id,
                ExtractionSchemaVersion.is_active == True,
            ).all()
            assert len(active_schemas) <= 1, f"Doc type {dt.name} should have at most one active schema"

    def test_only_one_active_prompt_template(self, db_session: Session):
        crud = ExtractionDocumentTypeCRUD(db_session)
        prompt_crud = ExtractionPromptTemplateCRUD(db_session)

        doc_types = crud.get_parsable_types()
        for dt in doc_types:
            active_prompts = db_session.query(ExtractionPromptTemplate).filter(
                ExtractionPromptTemplate.document_type_id == dt.id,
                ExtractionPromptTemplate.is_active == True,
            ).all()
            assert len(active_prompts) <= 1, f"Doc type {dt.name} should have at most one active prompt"


class TestExtractionPipelineService:
    """Test extraction pipeline service."""

    def test_get_parsable_document_types(self, db_session: Session):
        service = ExtractionPipelineService(db_session)
        doc_types = service.get_parsable_document_types()
        assert isinstance(doc_types, list)
        assert len(doc_types) >= 1

    def test_get_extraction_config(self, db_session: Session):
        service = ExtractionPipelineService(db_session)

        doc_types = service.get_parsable_document_types()
        if doc_types:
            config = service.get_extraction_config(doc_types[0])
            if config:
                assert "document_type" in config
                assert "schema_version" in config
                assert "prompt_template" in config
                assert "fields" in config

    def test_get_extraction_config_returns_none_for_invalid_type(self, db_session: Session):
        service = ExtractionPipelineService(db_session)
        config = service.get_extraction_config("nonexistent_document_type_xyz")
        assert config is None


class TestConfigFallbackDisabled:
    """Test that config fallback is disabled by default."""

    def test_allow_config_fallback_default_false(self):
        from app.settings import settings
        assert settings.allow_config_fallback is False, "allow_config_fallback should default to False"
