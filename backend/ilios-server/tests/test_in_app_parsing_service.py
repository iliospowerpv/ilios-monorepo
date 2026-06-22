"""Tests for InAppParsingService.

Tests the in-app AI document parsing functionality using mocked OpenAI responses.
"""

import json
import os
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.services.in_app_parsing_service import (
    InAppParsingService,
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text,
    is_rate_limit_error,
)


class TestTextExtraction:
    """Tests for text extraction utilities."""

    def test_extract_text_pdf_extension(self):
        """Test that PDF files are routed to PDF extraction."""
        with patch("app.services.in_app_parsing_service.extract_text_from_pdf") as mock_pdf:
            mock_pdf.return_value = "PDF text"
            result = extract_text(b"fake bytes", "document.pdf")
            mock_pdf.assert_called_once()
            assert result == "PDF text"

    def test_extract_text_docx_extension(self):
        """Test that DOCX files are routed to DOCX extraction."""
        with patch("app.services.in_app_parsing_service.extract_text_from_docx") as mock_docx:
            mock_docx.return_value = "DOCX text"
            result = extract_text(b"fake bytes", "document.docx")
            mock_docx.assert_called_once()
            assert result == "DOCX text"

    def test_extract_text_unsupported_extension(self):
        """Test that unsupported file types raise ValueError."""
        with pytest.raises(ValueError) as excinfo:
            extract_text(b"fake bytes", "document.xlsx")
        assert "Unsupported file type" in str(excinfo.value)

    def test_extract_text_uppercase_extension(self):
        """Test that extension matching is case-insensitive."""
        with patch("app.services.in_app_parsing_service.extract_text_from_pdf") as mock_pdf:
            mock_pdf.return_value = "PDF text"
            extract_text(b"fake bytes", "document.PDF")
            mock_pdf.assert_called_once()


class TestRateLimitErrorDetection:
    """Tests for rate limit error detection."""

    def test_detects_429_error(self):
        """Test detection of 429 status code in error message."""
        assert is_rate_limit_error(Exception("Request failed with 429"))

    def test_detects_ratelimit_exceeded(self):
        """Test detection of RATELIMIT_EXCEEDED message."""
        assert is_rate_limit_error(Exception("RATELIMIT_EXCEEDED: too many requests"))

    def test_detects_quota_error(self):
        """Test detection of quota-related errors."""
        assert is_rate_limit_error(Exception("Quota exceeded for this operation"))

    def test_detects_rate_limit_text(self):
        """Test detection of 'rate limit' text."""
        assert is_rate_limit_error(Exception("Rate limit reached for model"))

    def test_ignores_non_rate_limit_errors(self):
        """Test that non-rate-limit errors return False."""
        assert not is_rate_limit_error(Exception("File not found"))
        assert not is_rate_limit_error(Exception("Connection timeout"))


class TestInAppParsingServiceInit:
    """Tests for InAppParsingService initialization."""

    def test_check_openai_available_with_env_vars(self):
        """Test that check_openai_available returns True when env vars are set."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        with patch.dict(os.environ, {
            "AI_INTEGRATIONS_OPENAI_API_KEY": "test-key",
            "AI_INTEGRATIONS_OPENAI_BASE_URL": "http://test.url",
        }):
            assert service.check_openai_available() is True

    def test_check_openai_available_without_env_vars(self):
        """Test that check_openai_available returns False when env vars are missing."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        with patch.dict(os.environ, {}, clear=True):
            env_backup = {
                "AI_INTEGRATIONS_OPENAI_API_KEY": os.environ.pop("AI_INTEGRATIONS_OPENAI_API_KEY", None),
                "AI_INTEGRATIONS_OPENAI_BASE_URL": os.environ.pop("AI_INTEGRATIONS_OPENAI_BASE_URL", None),
            }
            try:
                assert service.check_openai_available() is False
            finally:
                for k, v in env_backup.items():
                    if v is not None:
                        os.environ[k] = v


class TestInAppParsingServiceParseFile:
    """Tests for the parse_file method."""

    @pytest.fixture
    def mock_file(self):
        """Create a mock file object."""
        file = MagicMock()
        file.id = 123
        file.filename = "lease_agreement.pdf"
        file.storage_key = "ilios/companies/1/sites/1/documents/1/2026-01-01_lease.pdf"
        file.filepath = None
        return file

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_extraction_config(self):
        """Create mock extraction configuration."""
        return {
            "document_type": {"id": 1, "name": "lease_agreement"},
            "schema_version": {"id": 1},
            "prompt_template": {
                "id": 1,
                "system_prompt": "You are a document extraction assistant.",
                "extraction_prompt": "Extract fields from: {document_text}",
                "model_name": "gpt-5.2",
                "temperature": 0.1,
                "max_tokens": 4096,
            },
            "fields": [{"name": "term_start", "display_name": "Term Start Date"}],
        }

    def test_parse_file_success(self, mock_file, mock_db_session):
        """Test successful file parsing."""
        service = InAppParsingService(mock_db_session)
        
        with patch.object(service, "download_file_bytes") as mock_download, \
             patch("app.services.in_app_parsing_service.extract_text") as mock_extract, \
             patch.object(service.pipeline_service, "build_extraction_prompt") as mock_build, \
             patch.object(service, "call_llm") as mock_llm, \
             patch.object(service.ai_results_crud, "update_by_id") as mock_update:
            
            mock_download.return_value = b"PDF bytes"
            mock_extract.return_value = "Lease agreement text with 500 characters of content for testing"
            mock_build.return_value = {
                "system_prompt": "You are an extraction assistant.",
                "user_prompt": "Extract from: lease text",
                "model_config": {"model_name": "gpt-5.2", "max_tokens": 4096, "temperature": 0.1},
                "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            }
            mock_llm.return_value = {"term_start": {"value": "2026-01-01"}}
            
            result = service.parse_file(mock_file, ai_result_id=1, document_type_name="Lease Agreement")
            
            assert result["status"] == "completed"
            assert result["parsed_result"] == {"term_start": {"value": "2026-01-01"}}
            mock_update.assert_called()

    def test_parse_file_download_failure(self, mock_file, mock_db_session):
        """Test parsing failure when file download fails."""
        service = InAppParsingService(mock_db_session)
        
        with patch.object(service, "download_file_bytes") as mock_download, \
             patch.object(service.ai_results_crud, "update_by_id") as mock_update:
            
            mock_download.side_effect = ValueError("Storage error")
            
            with pytest.raises(ValueError, match="Storage error"):
                service.parse_file(mock_file, ai_result_id=1, document_type_name="Lease Agreement")
            
            mock_update.assert_called()
            call_args = mock_update.call_args[0]
            assert call_args[0] == 1

    def test_parse_file_no_extraction_config(self, mock_file, mock_db_session):
        """Test parsing failure when extraction config not found."""
        service = InAppParsingService(mock_db_session)
        
        with patch.object(service, "download_file_bytes") as mock_download, \
             patch("app.services.in_app_parsing_service.extract_text") as mock_extract, \
             patch.object(service.pipeline_service, "build_extraction_prompt") as mock_build, \
             patch.object(service.ai_results_crud, "update_by_id"):
            
            mock_download.return_value = b"PDF bytes"
            mock_extract.return_value = "Text content with enough chars for validation testing"
            mock_build.return_value = None
            
            with pytest.raises(ValueError, match="No extraction config found"):
                service.parse_file(mock_file, ai_result_id=1, document_type_name="Unknown Type")

    def test_parse_file_empty_document(self, mock_file, mock_db_session):
        """Test parsing failure when document has too little text."""
        service = InAppParsingService(mock_db_session)
        
        with patch.object(service, "download_file_bytes") as mock_download, \
             patch("app.services.in_app_parsing_service.extract_text") as mock_extract, \
             patch.object(service.ai_results_crud, "update_by_id"):
            
            mock_download.return_value = b"PDF bytes"
            mock_extract.return_value = "Short"
            
            with pytest.raises(ValueError, match="Extracted text too short"):
                service.parse_file(mock_file, ai_result_id=1, document_type_name="Lease Agreement")


class TestInAppParsingServiceLLMCall:
    """Tests for the LLM call method."""

    def test_call_llm_success(self):
        """Test successful LLM call with JSON response."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"field1": "value1"}'
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch.object(service, "_openai_client", mock_client):
            service._openai_client = mock_client
            result = service.call_llm("system prompt", "user prompt")
            
            assert result == {"field1": "value1"}

    def test_call_llm_invalid_json(self):
        """Test LLM call with non-JSON response raises error."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON"
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch.object(service, "_openai_client", mock_client):
            service._openai_client = mock_client
            with pytest.raises(ValueError, match="not valid JSON"):
                service.call_llm("system prompt", "user prompt")

    def test_call_llm_empty_response(self):
        """Test LLM call with empty response raises error."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch.object(service, "_openai_client", mock_client):
            service._openai_client = mock_client
            with pytest.raises(ValueError, match="Empty response"):
                service.call_llm("system prompt", "user prompt")

    def test_call_llm_upgrades_legacy_model(self):
        """Test that legacy GPT-4 models are upgraded to GPT-5.2."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": "ok"}'
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        with patch.object(service, "_openai_client", mock_client):
            service._openai_client = mock_client
            service.call_llm("system", "user", model_name="gpt-4o")
            
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-5.2"


class TestModelSelectionGuard:
    """Protects the call_llm model-selection fallback guard.

    A stale extraction template can point at a model the Replit AI gateway no
    longer serves (e.g. ``claude-*`` names, or older ``gpt-4*`` variants). That
    previously failed every parse run with a 400 UNSUPPORTED_MODEL error. The
    guard in ``call_llm`` must remap any unsupported/legacy name to the supported
    default while leaving already-supported names (``gpt-5*``, ``gpt-4.1*``)
    untouched. These tests monkeypatch the OpenAI client so they never hit the
    real gateway and stay deterministic.
    """

    DEFAULT_MODEL = "gpt-5.2"

    def _make_service(self):
        """Build a service whose OpenAI client records the model it was called with."""
        service = InAppParsingService(MagicMock())

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"ok": true}'

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        service._openai_client = mock_client
        return service, mock_client

    def _model_used(self, model_name):
        service, mock_client = self._make_service()
        service.call_llm("system prompt", "user prompt", model_name=model_name)
        return mock_client.chat.completions.create.call_args[1]["model"]

    @pytest.mark.parametrize(
        "legacy_model",
        [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus",
            "claude-sonnet-4-20250514",
            "gpt-4",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "text-davinci-003",
            "some-unknown-model",
        ],
    )
    def test_unsupported_models_fall_back_to_default(self, legacy_model):
        """Any unsupported/legacy model name is remapped to the supported default."""
        assert self._model_used(legacy_model) == self.DEFAULT_MODEL

    @pytest.mark.parametrize(
        "supported_model",
        [
            "gpt-5",
            "gpt-5.2",
            "gpt-5-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
        ],
    )
    def test_supported_models_pass_through_unchanged(self, supported_model):
        """Already-supported model names are sent to the gateway unchanged."""
        assert self._model_used(supported_model) == supported_model

    @pytest.mark.parametrize("empty_model", ["", None])
    def test_empty_model_uses_default(self, empty_model):
        """A missing/empty configured model resolves to the supported default."""
        assert self._model_used(empty_model) == self.DEFAULT_MODEL


class TestDownloadFileBytes:
    """Tests for file download from storage."""

    def test_download_from_replit_storage(self):
        """Test downloading file from Replit storage."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        mock_file = MagicMock()
        mock_file.id = 1
        mock_file.storage_key = "ilios/test/file.pdf"
        mock_file.filepath = None
        
        with patch("app.services.in_app_parsing_service.get_storage_service") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.download_bytes.return_value = b"file content"
            mock_get_storage.return_value = mock_storage
            
            result = service.download_file_bytes(mock_file)
            
            assert result == b"file content"
            mock_storage.download_bytes.assert_called_with("ilios/test/file.pdf")

    def test_download_legacy_gcs_raises_error(self):
        """Test that legacy GCS files raise appropriate error."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        mock_file = MagicMock()
        mock_file.id = 1
        mock_file.storage_key = None
        mock_file.filepath = "legacy/gcs/path.pdf"
        
        with pytest.raises(ValueError, match="legacy GCS storage"):
            service.download_file_bytes(mock_file)

    def test_download_no_storage_key_or_filepath(self):
        """Test that files without storage info raise error."""
        mock_db = MagicMock()
        service = InAppParsingService(mock_db)
        
        mock_file = MagicMock()
        mock_file.id = 1
        mock_file.storage_key = None
        mock_file.filepath = None
        
        with pytest.raises(ValueError, match="no storage_key or filepath"):
            service.download_file_bytes(mock_file)
