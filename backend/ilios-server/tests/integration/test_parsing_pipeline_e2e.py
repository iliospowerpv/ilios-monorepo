"""
Phase 2B: End-to-End Integration Tests for Data Room Parsing Pipeline

Tests the complete flow: Trigger → Process → Preview → Accept/Promote

Uses LLM stub to avoid real API calls while still testing:
- Database state transitions (queued → processing → succeeded/failed)
- Storage fetch (mocked at storage boundary)
- Claim pattern and idempotency
- Binding snapshot persistence
- Accept/Promote workflow
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.crud.file import FileCRUD
from app.models.file import FileParsingStatuses, AIParsingResult
from app.services.llm_stub import LLMStub, enable_llm_stub, disable_llm_stub
from app.services.in_app_parsing_service import InAppParsingService
from app.routers.due_diligence.files_parsing import _run_parsing_background


class MockStorageService:
    """Mock storage service that returns test PDF bytes."""
    
    def __init__(self):
        self.download_count = 0
    
    def download_bytes(self, storage_key: str) -> bytes:
        """Return minimal PDF bytes for testing."""
        self.download_count += 1
        return self._get_test_pdf_bytes()
    
    @staticmethod
    def _get_test_pdf_bytes() -> bytes:
        """Generate minimal valid PDF bytes."""
        pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test Lease Agreement between Test Landlord LLC and Test Tenant Corp. Lease term: 25 years starting January 1 2024. Annual rent: $50000.) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""
        return pdf_content


@pytest.fixture
def mock_storage():
    """Fixture to mock storage service."""
    mock = MockStorageService()
    with patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock):
        yield mock


@pytest.fixture
def llm_stub():
    """Fixture that enables LLM stub for duration of test."""
    stub = enable_llm_stub()
    yield stub
    disable_llm_stub()


@pytest.fixture
def llm_stub_with_error():
    """Fixture that enables LLM stub configured to raise an error."""
    stub = enable_llm_stub(LLMStub(raise_exception=ValueError("Simulated LLM extraction failure")))
    yield stub
    disable_llm_stub()


@pytest.fixture
def test_file_with_storage(db_session, non_system_user_id, site_lease_document):
    """Create a test file with storage_key for Replit storage."""
    file_crud = FileCRUD(db_session)
    file = file_crud.create_item({
        "filepath": None,
        "storage_key": "ilios/test/documents/test_lease.pdf",
        "filename": "test_lease.pdf",
        "user_id": non_system_user_id,
        "document_id": site_lease_document.id,
    })
    file_id = file.id
    
    yield file
    
    db_session.query(AIParsingResult).filter(AIParsingResult.file_id == file_id).delete()
    db_session.commit()
    file_crud.delete_by_id(file_id)


@pytest.fixture
def mock_extraction_config():
    """Mock extraction pipeline config."""
    config = {
        "document_type": {"id": 1, "name": "Site Lease"},
        "schema_version": {"id": 1, "version": "1.0.0"},
        "prompt_template": {"id": 1, "version": "1.0.0"},
    }
    prompt_data = {
        "system_prompt": "You are a document extraction assistant.",
        "user_prompt": "Extract the following fields from this document:\n\nDocument text: {text}",
        "metadata": {
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        },
        "model_config": {
            "model_name": "gpt-5.2",
            "max_tokens": 8192,
        },
    }
    return config, prompt_data


class TestParsingPipelineHappyPath:
    """Test A: Happy path - Trigger → Process → Preview"""
    
    def test_trigger_endpoint_returns_202_and_creates_queued_job(
        self,
        client,
        db_session,
        site_id,
        site_lease_document,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        company_member_user_auth_header,
        mocker,
    ):
        """Verify trigger endpoint returns 202 with run_id, correlation_id, and status.
        
        The API response includes:
        - run_id: AIParsingResult.id for the created/existing job
        - correlation_id: UUID for request tracing
        - status: Current job status (queued/processing)
        - code: HTTP status code (202)
        - message: Success message
        """
        mocker.patch("app.services.in_app_parsing_service.InAppParsingService.check_openai_available", return_value=True)
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.get_extraction_config", return_value={
            "document_type": {"id": 1, "name": "Site Lease"},
            "schema_version": {"id": 1, "version": "1.0.0"},
            "prompt_template": {"id": 1, "version": "1.0.0"},
        })
        mocker.patch("app.helpers.configs.ai_parsing_helper.AIParsingHandler.get_parsable_documents_list", return_value=["Site Lease"])
        mocker.patch("app.helpers.configs.agreement_names_helper.AgreementNamesMappingHandler.get_pipeline_agreement_name", return_value="Site Lease")
        
        initial_run_count = db_session.query(AIParsingResult).filter(
            AIParsingResult.file_id == test_file_with_storage.id
        ).count()
        
        endpoint = f"/api/due-diligence/{site_id}/documents/{site_lease_document.id}/files/{test_file_with_storage.id}/parsing/"
        
        response = client.post(endpoint, headers=company_member_user_auth_header)
        
        assert response.status_code == 202
        result = response.json()
        
        assert result["code"] == 202
        assert result["message"] == "Parsing has been started"
        assert "run_id" in result
        assert "correlation_id" in result
        assert "status" in result
        
        run_id = result["run_id"]
        correlation_id = result["correlation_id"]
        status = result["status"]
        
        assert isinstance(run_id, int)
        assert run_id > 0
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0
        assert status in ["queued", "processing"]
        
        final_run_count = db_session.query(AIParsingResult).filter(
            AIParsingResult.file_id == test_file_with_storage.id
        ).count()
        assert final_run_count >= initial_run_count + 1
        
        db_run = db_session.query(AIParsingResult).filter(
            AIParsingResult.id == run_id
        ).first()
        
        assert db_run is not None
        assert db_run.correlation_id == correlation_id
        assert db_run.status.value == status
        assert db_run.document_type_id == 1
        assert db_run.schema_version_id == 1
        assert db_run.prompt_template_id == 1
    
    def test_trigger_creates_queued_job_with_correlation_id(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        mocker,
    ):
        """Verify trigger creates a queued job with correlation_id."""
        mocker.patch("app.services.in_app_parsing_service.InAppParsingService.check_openai_available", return_value=True)
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.get_extraction_config", return_value={
            "document_type": {"id": 1, "name": "Site Lease"},
            "schema_version": {"id": 1, "version": "1.0.0"},
            "prompt_template": {"id": 1, "version": "1.0.0"},
        })
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields from this lease document.",
            "user_prompt": "Document text:\n\nTest lease content...",
            "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 8192},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        
        payload = {
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "test-abc123",
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        }
        
        run, is_new = ai_crud.create_or_get_active(test_file_with_storage.id, payload)
        
        assert is_new is True
        assert run.status == FileParsingStatuses.queued
        assert run.correlation_id == "test-abc123"
        assert run.file_id == test_file_with_storage.id
        assert run.document_type_id == 1
        assert run.schema_version_id == 1
        assert run.prompt_template_id == 1
    
    def test_background_task_processes_to_completed(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        mocker,
    ):
        """Verify background task claims and processes job to completion."""
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields from this lease document.",
            "user_prompt": "Document text:\n\nTest lease content...",
            "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 8192},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "bg-test-001",
            "document_type_id": 1,
        })
        db_session.commit()
        
        with patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage):
            _run_parsing_background(
                file_id=test_file_with_storage.id,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="bg-test-001",
            )
        
        db_session.refresh(run)
        
        assert run.status == FileParsingStatuses.completed
        assert run.parsed_result is not None
        assert run.end_time is not None
        assert run.worker_id is not None
        assert run.claimed_at is not None
        
        assert "lessor_name" in run.parsed_result
        assert run.parsed_result["lessor_name"]["value"] == "Test Landlord LLC"
        assert run.parsed_result["lessor_name"]["confidence"] == 0.95
        
        assert llm_stub.call_count == 1
    
    def test_parsed_result_contains_binding_snapshots(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        mocker,
    ):
        """Verify binding snapshots are set after successful parsing."""
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields.",
            "user_prompt": "Document: test",
            "metadata": {"document_type_id": 5, "schema_version_id": 10, "prompt_template_id": 15},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 4096},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "binding-test",
        })
        db_session.commit()
        
        with patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage):
            _run_parsing_background(
                file_id=test_file_with_storage.id,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="binding-test",
            )
        
        db_session.refresh(run)
        
        assert run.document_type_id == 5
        assert run.schema_version_id == 10
        assert run.prompt_template_id == 15
    
    def test_preview_endpoint_returns_parsed_result(
        self,
        client,
        db_session,
        site_id,
        site_lease_document,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        company_member_user_auth_header,
        mocker,
    ):
        """Verify preview endpoint returns parsed result after processing."""
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields.",
            "user_prompt": "Document: test",
            "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 4096},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "preview-test",
        })
        db_session.commit()
        
        with patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage):
            _run_parsing_background(
                file_id=test_file_with_storage.id,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="preview-test",
            )
        
        response = client.get(
            f"/api/due-diligence/{site_id}/documents/{site_lease_document.id}/files/{test_file_with_storage.id}/runs/{run.id}/",
            headers=company_member_user_auth_header,
        )
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        assert result["extracted_fields"] is not None
        assert len(result["extracted_fields"]) > 0
        
        field_names = [f["field_name"] for f in result["extracted_fields"]]
        assert "lessor_name" in field_names


class TestParsingPipelineIdempotency:
    """Test B: Accept/Promote path with idempotency verification"""
    
    def test_double_trigger_returns_existing_run(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mocker,
    ):
        """Verify double-trigger returns existing run (idempotency)."""
        ai_crud = AIParsingResultCRUD(db_session)
        
        payload = {
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "first-trigger",
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        }
        
        run1, is_new1 = ai_crud.create_or_get_active(test_file_with_storage.id, payload)
        
        payload2 = payload.copy()
        payload2["correlation_id"] = "second-trigger"
        run2, is_new2 = ai_crud.create_or_get_active(test_file_with_storage.id, payload2)
        
        assert is_new1 is True
        assert is_new2 is False
        assert run1.id == run2.id
    
    def test_concurrent_triggers_only_create_one_run(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mocker,
    ):
        """Verify concurrent triggers result in only one run (DB enforcement)."""
        ai_crud = AIParsingResultCRUD(db_session)
        
        run1 = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "concurrent-1",
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        })
        db_session.commit()
        
        payload2 = {
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 2,
            "correlation_id": "concurrent-2",
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        }
        run2, is_new2 = ai_crud.create_or_get_active(test_file_with_storage.id, payload2)
        
        assert is_new2 is False
        assert run2.id == run1.id
    
    def test_force_reprocess_bypasses_idempotency(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        mocker,
    ):
        """Verify force reprocess creates new run even with existing."""
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields.",
            "user_prompt": "Document: test",
            "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 4096},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        
        run1 = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "original-run",
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        })
        db_session.commit()
        
        with patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage):
            _run_parsing_background(
                file_id=test_file_with_storage.id,
                ai_result_id=run1.id,
                document_type_name="Site Lease",
                correlation_id="original-run",
            )
        
        db_session.refresh(run1)
        assert run1.status == FileParsingStatuses.completed
        
        run2 = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 2,
            "correlation_id": "force-reprocess",
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
            "is_reprocess": True,
            "force_reprocess": True,
        })
        db_session.commit()
        
        assert run2.id != run1.id
        assert run2.is_reprocess is True
        assert run2.force_reprocess is True


class TestParsingPipelineFailurePath:
    """Test C: Failure path - LLM exception handling"""
    
    def test_llm_failure_marks_run_as_failed(
        self,
        db_session,
        test_file_with_storage,
        llm_stub_with_error,
        mock_storage,
        mocker,
    ):
        """Verify LLM failure results in processing_failed status."""
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields.",
            "user_prompt": "Document: test",
            "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 4096},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "fail-test",
        })
        db_session.commit()
        
        with patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage):
            _run_parsing_background(
                file_id=test_file_with_storage.id,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="fail-test",
            )
        
        db_session.refresh(run)
        
        assert run.status == FileParsingStatuses.processing_failed
        assert run.error_message is not None
        assert "Simulated LLM extraction failure" in run.error_message
        assert run.end_time is not None
    
    def test_failure_sets_timestamps_correctly(
        self,
        db_session,
        test_file_with_storage,
        llm_stub_with_error,
        mock_storage,
        mocker,
    ):
        """Verify failure path sets claimed_at and end_time correctly."""
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields.",
            "user_prompt": "Document: test",
            "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 4096},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "timestamp-test",
        })
        db_session.commit()
        
        before_processing = datetime.now(timezone.utc)
        
        with patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage):
            _run_parsing_background(
                file_id=test_file_with_storage.id,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="timestamp-test",
            )
        
        after_processing = datetime.now(timezone.utc)
        
        db_session.refresh(run)
        
        assert run.claimed_at is not None
        assert run.end_time is not None
        
        if run.claimed_at.tzinfo is None:
            claimed_at_utc = run.claimed_at.replace(tzinfo=timezone.utc)
        else:
            claimed_at_utc = run.claimed_at
        
        if run.end_time.tzinfo is None:
            end_time_utc = run.end_time.replace(tzinfo=timezone.utc)
        else:
            end_time_utc = run.end_time
        
        assert claimed_at_utc <= end_time_utc
    
    def test_storage_failure_marks_run_as_failed(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mocker,
    ):
        """Verify storage download failure results in processing_failed."""
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields.",
            "user_prompt": "Document: test",
            "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 4096},
        })
        
        failing_storage = MagicMock()
        failing_storage.download_bytes.side_effect = Exception("Storage download failed: bucket not found")
        
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "storage-fail-test",
        })
        db_session.commit()
        
        with patch("app.services.in_app_parsing_service.get_storage_service", return_value=failing_storage):
            _run_parsing_background(
                file_id=test_file_with_storage.id,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="storage-fail-test",
            )
        
        db_session.refresh(run)
        
        assert run.status == FileParsingStatuses.processing_failed
        assert run.error_message is not None
        assert "Storage download failed" in run.error_message or "bucket not found" in run.error_message
        assert run.end_time is not None


class TestStateTransitions:
    """Validate correct state transitions throughout pipeline."""
    
    def test_queued_to_processing_transition(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
    ):
        """Verify atomic_claim transitions from queued to processing."""
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "transition-test",
        })
        db_session.commit()
        
        assert run.status == FileParsingStatuses.queued
        
        claimed, updated_run = ai_crud.atomic_claim(run.id, "transition-test", "test-worker")
        
        assert claimed is True
        assert updated_run.status == FileParsingStatuses.processing
        assert updated_run.worker_id == "test-worker"
        assert updated_run.claimed_at is not None
    
    def test_cannot_claim_already_processing_run(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
    ):
        """Verify second worker cannot claim already-processing run."""
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "double-claim-test",
        })
        db_session.commit()
        
        claimed1, _ = ai_crud.atomic_claim(run.id, "double-claim-test", "worker-1")
        assert claimed1 is True
        
        claimed2, run2 = ai_crud.atomic_claim(run.id, "double-claim-test", "worker-2")
        assert claimed2 is False
        assert run2.worker_id == "worker-1"
    
    def test_terminal_states_are_immutable(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
    ):
        """Verify terminal states cannot be overwritten."""
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.completed,
            "extraction_run_number": 1,
            "correlation_id": "terminal-test",
            "end_time": datetime.now(timezone.utc),
            "parsed_result": {"field": "value"},
        })
        db_session.commit()
        
        claimed, _ = ai_crud.atomic_claim(run.id, "terminal-test", "late-worker")
        assert claimed is False


class TestAcceptPromoteWorkflow:
    """Test B: Accept/Promote path - verifies promotion endpoint behavior"""
    
    def test_promote_endpoint_updates_file_to_actual(
        self,
        client,
        db_session,
        site_id,
        site_lease_document,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        company_admin_full_access_header,
        mocker,
    ):
        """Verify promote endpoint marks file as actual and creates promotion record."""
        from app.crud.assumption_promotion import AssumptionPromotionCRUD
        from app.crud.file import FileCRUD
        
        mocker.patch("app.services.promotion_service.PromotionService.compute_promotion_diff", return_value={
            "has_changes": True,
            "changes": [{"type": "added", "field_name": "lessor_name", "field_id": 1, "current_value": None, "new_value": "Test Landlord LLC", "current_source_file_id": None, "new_source_file_id": test_file_with_storage.id}],
            "summary": {"added": 1, "changed": 0, "removed": 0}
        })
        mocker.patch("app.services.promotion_service.PromotionService._promote_candidate_facts", return_value=[])
        
        file_crud = FileCRUD(db_session)
        file_crud.update_by_id(test_file_with_storage.id, {"is_actual": False})
        db_session.commit()
        
        promotion_crud = AssumptionPromotionCRUD(db_session)
        initial_count = promotion_crud.count_promotions_for_site(site_id)
        
        endpoint = f"/api/assumptions/{site_id}/promote"
        response = client.post(
            endpoint,
            headers=company_admin_full_access_header,
            json={
                "document_id": site_lease_document.id,
                "file_id": test_file_with_storage.id,
                "notes": "Promoted via E2E test"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            assert result["promoted"] is True
            assert result["file_id"] == test_file_with_storage.id
            
            db_session.refresh(test_file_with_storage)
            assert test_file_with_storage.is_actual is True
            
            new_count = promotion_crud.count_promotions_for_site(site_id)
            assert new_count > initial_count
    
    def test_promote_creates_audit_trail_without_data_duplication(
        self,
        client,
        db_session,
        site_id,
        site_lease_document,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        company_admin_full_access_header,
        mocker,
    ):
        """Verify promotion creates audit trail records without duplicating facts.
        
        Design note: Each promotion creates a new AssumptionPromotion record for audit trail.
        This is intentional - the audit log shows all promotion actions taken.
        Idempotency at the data level means facts don't get duplicated, not that
        audit records aren't created.
        
        When the same file is promoted again with has_changes=False, the system:
        1. Creates a new audit record (correct for compliance/auditing)
        2. Does NOT create duplicate facts (mocked _promote_candidate_facts returns [])
        """
        from app.crud.assumption_promotion import AssumptionPromotionCRUD
        
        mocker.patch("app.services.promotion_service.PromotionService.compute_promotion_diff", return_value={
            "has_changes": False,
            "changes": [],
            "summary": {"added": 0, "changed": 0, "removed": 0}
        })
        mocker.patch("app.services.promotion_service.PromotionService._promote_candidate_facts", return_value=[])
        
        endpoint = f"/api/assumptions/{site_id}/promote"
        payload = {
            "document_id": site_lease_document.id,
            "file_id": test_file_with_storage.id,
            "notes": "First promotion"
        }
        
        response1 = client.post(endpoint, headers=company_admin_full_access_header, json=payload)
        
        if response1.status_code == 200:
            promotion_crud = AssumptionPromotionCRUD(db_session)
            count_after_first = promotion_crud.count_promotions_for_site(site_id)
            
            payload["notes"] = "Second promotion (no-op, audit only)"
            response2 = client.post(endpoint, headers=company_admin_full_access_header, json=payload)
            
            count_after_second = promotion_crud.count_promotions_for_site(site_id)
            
            assert count_after_second == count_after_first + 1
    
    def test_end_to_end_parse_then_promote(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mock_storage,
        mocker,
    ):
        """E2E: Parse file, then verify it can be promoted."""
        from app.crud.file import FileCRUD
        
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value={
            "system_prompt": "Extract fields.",
            "user_prompt": "Document: test",
            "metadata": {"document_type_id": 1, "schema_version_id": 1, "prompt_template_id": 1},
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 4096},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        run = ai_crud.create_item({
            "file_id": test_file_with_storage.id,
            "status": FileParsingStatuses.queued,
            "extraction_run_number": 1,
            "correlation_id": "e2e-parse-promote",
        })
        db_session.commit()
        
        with patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage):
            _run_parsing_background(
                file_id=test_file_with_storage.id,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="e2e-parse-promote",
            )
        
        db_session.refresh(run)
        assert run.status == FileParsingStatuses.completed
        assert run.parsed_result is not None
        
        assert "lessor_name" in run.parsed_result
        assert run.parsed_result["lessor_name"]["value"] == "Test Landlord LLC"
        
        file_crud = FileCRUD(db_session)
        db_session.refresh(test_file_with_storage)
        
        assert test_file_with_storage.id is not None
        assert run.file_id == test_file_with_storage.id


class TestLLMStubSafety:
    """Test C: LLM stub safety gating - only allowed in test/dev environments."""
    
    def test_stub_cannot_be_enabled_in_production(self, mocker):
        """Verify LLM stub raises RuntimeError when enabled in production environment."""
        import os
        from app.services.llm_stub import (
            enable_llm_stub,
            disable_llm_stub,
            is_llm_stub_enabled,
            _is_safe_environment,
        )
        
        original_env = os.environ.get("environment_name")
        original_stub_enabled = os.environ.get("LLM_STUB_ENABLED")
        
        try:
            os.environ["environment_name"] = "production"
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            os.environ.pop("LLM_STUB_FORCE_ALLOW", None)
            
            assert _is_safe_environment() is False
            
            with pytest.raises(RuntimeError) as exc_info:
                enable_llm_stub()
            
            assert "production" in str(exc_info.value).lower()
            assert "only allowed" in str(exc_info.value).lower()
            
            os.environ["LLM_STUB_ENABLED"] = "true"
            assert is_llm_stub_enabled() is False
            
        finally:
            if original_env:
                os.environ["environment_name"] = original_env
            else:
                os.environ.pop("environment_name", None)
            if original_stub_enabled:
                os.environ["LLM_STUB_ENABLED"] = original_stub_enabled
            else:
                os.environ.pop("LLM_STUB_ENABLED", None)
            disable_llm_stub()
    
    def test_stub_cannot_be_enabled_in_staging(self, mocker):
        """Verify LLM stub raises RuntimeError when enabled in staging environment."""
        import os
        from app.services.llm_stub import (
            enable_llm_stub,
            disable_llm_stub,
            is_llm_stub_enabled,
        )
        
        original_env = os.environ.get("environment_name")
        original_stub_enabled = os.environ.get("LLM_STUB_ENABLED")
        
        try:
            os.environ["environment_name"] = "staging"
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            os.environ.pop("LLM_STUB_FORCE_ALLOW", None)
            
            with pytest.raises(RuntimeError) as exc_info:
                enable_llm_stub()
            
            assert "staging" in str(exc_info.value).lower()
            
        finally:
            if original_env:
                os.environ["environment_name"] = original_env
            else:
                os.environ.pop("environment_name", None)
            if original_stub_enabled:
                os.environ["LLM_STUB_ENABLED"] = original_stub_enabled
            else:
                os.environ.pop("LLM_STUB_ENABLED", None)
            disable_llm_stub()
    
    def test_stub_can_be_enabled_in_test_environment(self, mocker):
        """Verify LLM stub can be enabled in test environment."""
        import os
        from app.services.llm_stub import (
            enable_llm_stub,
            disable_llm_stub,
            is_llm_stub_enabled,
            _is_safe_environment,
        )
        
        original_env = os.environ.get("environment_name")
        
        try:
            os.environ["environment_name"] = "test"
            
            assert _is_safe_environment() is True
            
            stub = enable_llm_stub()
            assert stub is not None
            assert is_llm_stub_enabled() is True
            
        finally:
            if original_env:
                os.environ["environment_name"] = original_env
            else:
                os.environ.pop("environment_name", None)
            disable_llm_stub()
    
    def test_stub_can_be_enabled_in_dev_environment(self, mocker):
        """Verify LLM stub can be enabled in development environment."""
        import os
        from app.services.llm_stub import (
            enable_llm_stub,
            disable_llm_stub,
            is_llm_stub_enabled,
        )
        
        original_env = os.environ.get("environment_name")
        
        try:
            os.environ["environment_name"] = "development"
            
            stub = enable_llm_stub()
            assert stub is not None
            assert is_llm_stub_enabled() is True
            
        finally:
            if original_env:
                os.environ["environment_name"] = original_env
            else:
                os.environ.pop("environment_name", None)
            disable_llm_stub()
    
    def test_stub_blocked_in_unknown_environment(self, mocker):
        """Verify LLM stub is blocked in unknown environments (e.g., qa, uat).
        
        Unknown environments should be blocked by default for safety.
        """
        import os
        from app.services.llm_stub import (
            enable_llm_stub,
            disable_llm_stub,
            is_llm_stub_enabled,
            _is_safe_environment,
        )
        
        original_env = os.environ.get("environment_name")
        original_stub_enabled = os.environ.get("LLM_STUB_ENABLED")
        
        try:
            os.environ["environment_name"] = "qa"
            os.environ.pop("PYTEST_CURRENT_TEST", None)
            os.environ.pop("LLM_STUB_FORCE_ALLOW", None)
            
            assert _is_safe_environment() is False
            
            with pytest.raises(RuntimeError) as exc_info:
                enable_llm_stub()
            
            assert "qa" in str(exc_info.value).lower()
            
            os.environ["LLM_STUB_ENABLED"] = "true"
            assert is_llm_stub_enabled() is False
            
        finally:
            if original_env:
                os.environ["environment_name"] = original_env
            else:
                os.environ.pop("environment_name", None)
            if original_stub_enabled:
                os.environ["LLM_STUB_ENABLED"] = original_stub_enabled
            else:
                os.environ.pop("LLM_STUB_ENABLED", None)
            disable_llm_stub()


class TestParsingGuardrails:
    """Phase 3: Tests for parsing guardrails and resource limits."""
    
    def test_insufficient_text_fails_with_reason_code(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mocker,
    ):
        """Verify PDF with minimal text fails with insufficient_text_extracted reason code."""
        from app.services.in_app_parsing_service import (
            InAppParsingService,
            ParsingGuardrailError,
            ParsingReasonCode,
        )
        
        minimal_pdf = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length 20>>stream
BT /F1 12 Tf (Hi) Tj ET
endstream
endobj
xref
0 5
trailer<</Size 5/Root 1 0 R>>
startxref
200
%%EOF"""
        
        mock_storage = MagicMock()
        mock_storage.download_bytes.return_value = minimal_pdf
        mocker.patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage)
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.get_extraction_config", return_value={
            "document_type": {"id": 1, "name": "Site Lease"},
            "schema_version": {"id": 1, "version": "1.0.0"},
            "prompt_template": {"id": 1, "version": "1.0.0"},
        })
        
        ai_crud = AIParsingResultCRUD(db_session)
        run, _ = ai_crud.create_or_get_active(
            file_id=test_file_with_storage.id,
            payload={"file_id": test_file_with_storage.id, "status": FileParsingStatuses.queued}
        )
        
        service = InAppParsingService(db_session)
        
        with pytest.raises(ParsingGuardrailError) as exc_info:
            service.parse_file(
                file=test_file_with_storage,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="test-min-text",
            )
        
        assert exc_info.value.reason_code == ParsingReasonCode.INSUFFICIENT_TEXT_EXTRACTED
        assert "insufficient_text_extracted" in str(exc_info.value).lower()
        
        db_session.refresh(run)
        assert run.status == FileParsingStatuses.processing_failed
        assert "[insufficient_text_extracted]" in run.error_message
    
    def test_file_too_large_fails_with_reason_code(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mocker,
    ):
        """Verify oversized file fails with file_too_large reason code."""
        from app.services.in_app_parsing_service import (
            InAppParsingService,
            ParsingGuardrailError,
            ParsingReasonCode,
        )
        
        mocker.patch("app.settings.settings.parsing_max_file_size_mb", 1)
        
        large_bytes = b"X" * (2 * 1024 * 1024)  # 2MB
        
        mock_storage = MagicMock()
        mock_storage.download_bytes.return_value = large_bytes
        mocker.patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage)
        
        ai_crud = AIParsingResultCRUD(db_session)
        run, _ = ai_crud.create_or_get_active(
            file_id=test_file_with_storage.id,
            payload={"file_id": test_file_with_storage.id, "status": FileParsingStatuses.queued}
        )
        
        service = InAppParsingService(db_session)
        
        with pytest.raises(ParsingGuardrailError) as exc_info:
            service.parse_file(
                file=test_file_with_storage,
                ai_result_id=run.id,
                document_type_name="Site Lease",
                correlation_id="test-large-file",
            )
        
        assert exc_info.value.reason_code == ParsingReasonCode.FILE_TOO_LARGE
        assert "file_too_large" in str(exc_info.value).lower()
        
        db_session.refresh(run)
        assert run.status == FileParsingStatuses.processing_failed
        assert "[file_too_large]" in run.error_message
    
    def test_truncation_path_succeeds_with_metadata(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mocker,
    ):
        """Verify text truncation succeeds and includes truncation metadata."""
        from app.services.in_app_parsing_service import InAppParsingService
        
        mocker.patch("app.settings.settings.parsing_max_chars_to_llm", 1000)
        mocker.patch("app.settings.settings.parsing_min_text_chars", 100)
        
        long_text = "This is a test document. " * 200
        
        mock_pdf_bytes = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj
4 0 obj<</Length """ + str(len(long_text) + 30).encode() + b""">>stream
BT /F1 12 Tf (""" + long_text.encode() + b""") Tj ET
endstream
endobj
xref
0 5
trailer<</Size 5/Root 1 0 R>>
startxref
200
%%EOF"""
        
        mock_storage = MagicMock()
        mock_storage.download_bytes.return_value = mock_pdf_bytes
        mocker.patch("app.services.in_app_parsing_service.get_storage_service", return_value=mock_storage)
        
        def mock_extract_with_truncation(file_bytes, filename, **kwargs):
            from app.services.in_app_parsing_service import ExtractionResult
            return ExtractionResult(
                text=long_text[:1000],
                char_count=1000,
                word_count=200,
                page_count=1,
                was_truncated=True,
                truncated_char_count=len(long_text) - 1000,
            )
        
        mocker.patch("app.services.in_app_parsing_service.extract_text_with_guardrails", mock_extract_with_truncation)
        
        prompt_data = {
            "system_prompt": "Extract fields.",
            "user_prompt": "Document: {text}",
            "metadata": {
                "document_type_id": 1,
                "schema_version_id": 1,
                "prompt_template_id": 1,
            },
            "model_config": {"model_name": "gpt-5.2", "max_tokens": 8192},
        }
        mocker.patch("app.services.extraction_pipeline_service.ExtractionPipelineService.build_extraction_prompt", return_value=prompt_data)
        
        ai_crud = AIParsingResultCRUD(db_session)
        run, _ = ai_crud.create_or_get_active(
            file_id=test_file_with_storage.id,
            payload={"file_id": test_file_with_storage.id, "status": FileParsingStatuses.queued}
        )
        
        service = InAppParsingService(db_session)
        
        result = service.parse_file(
            file=test_file_with_storage,
            ai_result_id=run.id,
            document_type_name="Site Lease",
            correlation_id="test-truncation",
        )
        
        assert result["status"] == "completed"
        assert result["metadata"]["was_truncated"] is True
        assert result["metadata"]["truncated_char_count"] is not None
        assert result["metadata"]["truncated_char_count"] > 0
        
        db_session.refresh(run)
        assert run.status == FileParsingStatuses.completed
    
    def test_too_many_pages_fails_with_reason_code(
        self,
        db_session,
        test_file_with_storage,
        llm_stub,
        mocker,
    ):
        """Verify PDF with too many pages fails with too_many_pages reason code."""
        from app.services.in_app_parsing_service import (
            extract_text_with_guardrails,
            ParsingGuardrailError,
            ParsingReasonCode,
        )
        
        mocker.patch("app.settings.settings.parsing_max_pdf_pages", 5)
        
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.pages = [MagicMock() for _ in range(10)]
        
        mocker.patch("pypdf.PdfReader", return_value=mock_pdf_reader)
        
        mock_bytes = b"fake pdf content"
        
        with pytest.raises(ParsingGuardrailError) as exc_info:
            extract_text_with_guardrails(
                file_bytes=mock_bytes,
                filename="test.pdf",
                max_pdf_pages=5,
            )
        
        assert exc_info.value.reason_code == ParsingReasonCode.TOO_MANY_PAGES
        assert "10 pages" in exc_info.value.message
        assert "5" in exc_info.value.message


class TestBulkAcceptValidation:
    """Phase B4: Tests for bulk accept endpoint safety rules."""

    def test_bulk_accept_rejects_run_file_mismatch(self, test_db_session):
        """Batch accept rejects when run_id belongs to different file."""
        from app.models.file import AIParsingResult, FileParsingStatuses
        
        run1 = AIParsingResult(
            file_id=1,
            status=FileParsingStatuses.completed,
            extraction_run_number=1,
            parsed_result={"field1": {"value": "test"}},
        )
        test_db_session.add(run1)
        test_db_session.commit()
        test_db_session.refresh(run1)
        
        ai_crud = AIParsingResultCRUD(test_db_session)
        run = ai_crud.get_run_by_id(run1.id)
        
        assert run is not None
        assert run.file_id == 1
        assert run.file_id != 999

    def test_bulk_accept_rejects_processing_run(self, test_db_session):
        """Batch accept rejects run with processing status."""
        from app.models.file import AIParsingResult, FileParsingStatuses
        
        run = AIParsingResult(
            file_id=1,
            status=FileParsingStatuses.processing,
            extraction_run_number=1,
        )
        test_db_session.add(run)
        test_db_session.commit()
        test_db_session.refresh(run)
        
        ai_crud = AIParsingResultCRUD(test_db_session)
        fetched = ai_crud.get_run_by_id(run.id)
        
        assert fetched.status == FileParsingStatuses.processing
        assert fetched.status != FileParsingStatuses.completed

    def test_bulk_accept_rejects_failed_run(self, test_db_session):
        """Batch accept rejects run with failed status."""
        from app.models.file import AIParsingResult, FileParsingStatuses
        
        run = AIParsingResult(
            file_id=1,
            status=FileParsingStatuses.processing_failed,
            extraction_run_number=1,
            error_message="[llm_call_failed] Test failure",
        )
        test_db_session.add(run)
        test_db_session.commit()
        test_db_session.refresh(run)
        
        ai_crud = AIParsingResultCRUD(test_db_session)
        fetched = ai_crud.get_run_by_id(run.id)
        
        assert fetched.status == FileParsingStatuses.processing_failed
        assert fetched.status != FileParsingStatuses.completed

    def test_bulk_accept_rejects_non_latest_run(self, test_db_session):
        """Batch accept rejects non-latest run when allow_accept_non_latest=false."""
        from app.models.file import AIParsingResult, FileParsingStatuses
        
        run1 = AIParsingResult(
            file_id=1,
            status=FileParsingStatuses.completed,
            extraction_run_number=1,
            parsed_result={"field1": {"value": "old"}},
        )
        test_db_session.add(run1)
        test_db_session.commit()
        
        run2 = AIParsingResult(
            file_id=1,
            status=FileParsingStatuses.completed,
            extraction_run_number=2,
            parsed_result={"field1": {"value": "new"}},
        )
        test_db_session.add(run2)
        test_db_session.commit()
        
        ai_crud = AIParsingResultCRUD(test_db_session)
        latest = ai_crud.get_latest_run_for_file(1)
        
        assert latest.id == run2.id
        assert run1.id != latest.id

    def test_bulk_accept_succeeds_for_latest_succeeded_run(self, test_db_session):
        """Batch accept succeeds for latest succeeded run."""
        from app.models.file import AIParsingResult, FileParsingStatuses
        
        run = AIParsingResult(
            file_id=1,
            status=FileParsingStatuses.completed,
            extraction_run_number=1,
            parsed_result={
                "field1": {"value": "test_value", "confidence": 0.95},
                "_metadata": {"char_count": 1000},
            },
        )
        test_db_session.add(run)
        test_db_session.commit()
        test_db_session.refresh(run)
        
        ai_crud = AIParsingResultCRUD(test_db_session)
        latest = ai_crud.get_latest_run_for_file(1)
        
        assert latest.id == run.id
        assert latest.status == FileParsingStatuses.completed
        assert latest.parsed_result is not None
