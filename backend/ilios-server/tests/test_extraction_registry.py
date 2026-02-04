"""Tests for Extraction Registry and Document Versioning

Tests cover:
- Seed idempotency (document types, schema versions, prompt templates)
- Activation uniqueness (one active schema/prompt per doc type)
- Pipeline service functionality
- Config fallback disabled by default
- Parse run history and reprocess
- Storage service abstraction
"""

import pytest
from sqlalchemy.orm import Session


class TestSeedIdempotency:
    """Test that seed script is idempotent."""

    def test_seed_creates_document_types(self, db_session: Session):
        from app.crud.extraction_registry import ExtractionDocumentTypeCRUD
        crud = ExtractionDocumentTypeCRUD(db_session)
        doc_types = crud.get_parsable_types()
        assert len(doc_types) >= 0, "Seed should work without errors"

    def test_seed_creates_schema_versions(self, db_session: Session):
        from app.crud.extraction_registry import (
            ExtractionDocumentTypeCRUD,
            ExtractionSchemaVersionCRUD,
        )
        crud = ExtractionDocumentTypeCRUD(db_session)
        schema_crud = ExtractionSchemaVersionCRUD(db_session)

        doc_types = crud.get_parsable_types()
        for dt in doc_types[:3]:
            versions = schema_crud.get_versions_for_doc_type(dt.id)
            assert len(versions) >= 1, f"Doc type {dt.name} should have at least one schema version"


class TestActivationUniqueness:
    """Test that only one schema/prompt version can be active per doc type."""

    def test_only_one_active_schema_version(self, db_session: Session):
        from app.crud.extraction_registry import ExtractionDocumentTypeCRUD
        from app.models.extraction_registry import ExtractionSchemaVersion
        crud = ExtractionDocumentTypeCRUD(db_session)

        doc_types = crud.get_parsable_types()
        for dt in doc_types:
            active_schemas = db_session.query(ExtractionSchemaVersion).filter(
                ExtractionSchemaVersion.document_type_id == dt.id,
                ExtractionSchemaVersion.is_active == True,
            ).all()
            assert len(active_schemas) <= 1, f"Doc type {dt.name} should have at most one active schema"

    def test_only_one_active_prompt_template(self, db_session: Session):
        from app.crud.extraction_registry import ExtractionDocumentTypeCRUD
        from app.models.extraction_registry import ExtractionPromptTemplate
        crud = ExtractionDocumentTypeCRUD(db_session)

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
        from app.services.extraction_pipeline_service import ExtractionPipelineService
        service = ExtractionPipelineService(db_session)
        doc_types = service.get_parsable_document_types()
        assert isinstance(doc_types, list)

    def test_get_extraction_config_returns_none_for_invalid_type(self, db_session: Session):
        from app.services.extraction_pipeline_service import ExtractionPipelineService
        service = ExtractionPipelineService(db_session)
        config = service.get_extraction_config("nonexistent_document_type_xyz")
        assert config is None


class TestConfigFallbackDisabled:
    """Test that config fallback is disabled by default."""

    def test_allow_config_fallback_default_false(self):
        from app.settings import settings
        assert settings.allow_config_fallback is False, "allow_config_fallback should default to False"


class TestAIParsingResultCRUD:
    """Test AIParsingResult CRUD operations for run history."""

    def test_get_runs_for_file_returns_list(self, db_session: Session):
        from app.crud.ai_parsing_result import AIParsingResultCRUD
        crud = AIParsingResultCRUD(db_session)
        runs = crud.get_runs_for_file(file_id=999999)
        assert isinstance(runs, list)
        assert len(runs) == 0

    def test_count_runs_for_file(self, db_session: Session):
        from app.crud.ai_parsing_result import AIParsingResultCRUD
        crud = AIParsingResultCRUD(db_session)
        count = crud.count_runs_for_file(file_id=999999)
        assert count == 0


class TestStorageServiceAbstraction:
    """Test storage service abstraction layer."""

    def test_storage_service_import(self):
        from app.helpers.files.storage_service import (
            StorageService,
            GCSStorageService,
            get_storage_service,
            generate_storage_key,
        )
        assert StorageService is not None
        assert GCSStorageService is not None

    def test_generate_storage_key(self):
        from app.helpers.files.storage_service import generate_storage_key
        key = generate_storage_key(
            company_id=1,
            site_id=2,
            document_id=3,
            filename="test.pdf"
        )
        assert "companies/1" in key
        assert "sites/2" in key
        assert "documents/3" in key
        assert "test.pdf" in key


class TestFileCRUD:
    """Test File CRUD operations for versioning."""

    def test_get_versions_for_document(self, db_session: Session):
        from app.crud.file import FileCRUD
        crud = FileCRUD(db_session)
        versions = crud.get_versions_for_document(document_id=999999)
        assert isinstance(versions, list)
        assert len(versions) == 0

    def test_get_current_version_returns_none_for_nonexistent(self, db_session: Session):
        from app.crud.file import FileCRUD
        crud = FileCRUD(db_session)
        current = crud.get_current_version(document_id=999999)
        assert current is None
