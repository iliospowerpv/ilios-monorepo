"""Tests for parsing idempotency and concurrency safety (Phase 2A).

Tests cover:
1. Double trigger returns same run (idempotency)
2. Atomic claim prevents race conditions
3. Terminal states set end_time correctly
"""
import os
import threading
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.models.file import AIParsingResult, FileParsingStatuses


class TestIdempotency:
    """Test idempotent behavior - double trigger returns existing run."""

    def test_find_active_run_returns_queued(self, db_session: Session):
        """find_active_run should return queued runs."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.queued,
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        })
        
        found = crud.find_active_run(
            file_id=999,
            document_type_id=1,
            schema_version_id=1,
            prompt_template_id=1,
        )
        
        assert found is not None
        assert found.id == run.id
        
        db_session.delete(run)
        db_session.commit()

    def test_find_active_run_returns_processing(self, db_session: Session):
        """find_active_run should return processing runs."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.processing,
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        })
        
        found = crud.find_active_run(
            file_id=999,
            document_type_id=1,
            schema_version_id=1,
            prompt_template_id=1,
        )
        
        assert found is not None
        assert found.id == run.id
        
        db_session.delete(run)
        db_session.commit()

    def test_find_active_run_ignores_completed(self, db_session: Session):
        """find_active_run should NOT return completed runs."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.completed,
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        })
        
        found = crud.find_active_run(
            file_id=999,
            document_type_id=1,
            schema_version_id=1,
            prompt_template_id=1,
        )
        
        assert found is None
        
        db_session.delete(run)
        db_session.commit()

    def test_find_active_run_filters_by_context(self, db_session: Session):
        """find_active_run should only match same extraction context."""
        crud = AIParsingResultCRUD(db_session)
        
        run1 = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.queued,
            "document_type_id": 1,
            "schema_version_id": 1,
            "prompt_template_id": 1,
        })
        
        found_same = crud.find_active_run(
            file_id=999,
            document_type_id=1,
            schema_version_id=1,
            prompt_template_id=1,
        )
        assert found_same is not None
        
        found_diff_schema = crud.find_active_run(
            file_id=999,
            document_type_id=1,
            schema_version_id=2,
            prompt_template_id=1,
        )
        assert found_diff_schema is None
        
        db_session.delete(run1)
        db_session.commit()


class TestAtomicClaim:
    """Test atomic claim pattern for concurrency safety."""

    def test_claim_succeeds_for_queued_run(self, db_session: Session):
        """atomic_claim should succeed for queued runs."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.queued,
        })
        
        success, claimed_run = crud.atomic_claim(run.id, "test-corr-123", "test-worker")
        
        assert success is True
        assert claimed_run is not None
        assert claimed_run.status == FileParsingStatuses.processing
        assert claimed_run.worker_id == "test-worker"
        assert claimed_run.correlation_id == "test-corr-123"
        assert claimed_run.claimed_at is not None
        assert claimed_run.start_time is not None
        
        db_session.delete(run)
        db_session.commit()

    def test_claim_fails_for_processing_run(self, db_session: Session):
        """atomic_claim should fail for already processing runs."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.processing,
            "worker_id": "other-worker",
        })
        
        success, returned_run = crud.atomic_claim(run.id, "test-corr", "new-worker")
        
        assert success is False
        assert returned_run is not None
        assert returned_run.status == FileParsingStatuses.processing
        
        db_session.delete(run)
        db_session.commit()

    def test_claim_fails_for_completed_run(self, db_session: Session):
        """atomic_claim should fail for completed runs."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.completed,
        })
        
        success, returned_run = crud.atomic_claim(run.id, "test-corr", "worker")
        
        assert success is False
        assert returned_run is not None
        assert returned_run.status == FileParsingStatuses.completed
        
        db_session.delete(run)
        db_session.commit()

    def test_claim_fails_for_nonexistent_run(self, db_session: Session):
        """atomic_claim should fail for non-existent runs."""
        crud = AIParsingResultCRUD(db_session)
        
        success, returned_run = crud.atomic_claim(999999, "test-corr", "worker")
        
        assert success is False
        assert returned_run is None


class TestTerminalStates:
    """Test terminal state handling and end_time guarantees."""

    def test_mark_completed_sets_end_time(self, db_session: Session):
        """mark_completed should set end_time."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.processing,
        })
        
        result = crud.mark_completed(run.id, {"field1": "value1"}, "raw response")
        
        assert result is not None
        assert result.status == FileParsingStatuses.completed
        assert result.end_time is not None
        assert result.parsed_result == {"field1": "value1"}
        assert result.raw_llm_response == "raw response"
        
        db_session.delete(run)
        db_session.commit()

    def test_mark_failed_sets_end_time(self, db_session: Session):
        """mark_failed should set end_time."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.processing,
        })
        
        result = crud.mark_failed(run.id, "Something went wrong", retries=2)
        
        assert result is not None
        assert result.status == FileParsingStatuses.processing_failed
        assert result.end_time is not None
        assert result.error_message == "Something went wrong"
        assert result.retries == 2
        
        db_session.delete(run)
        db_session.commit()

    def test_mark_completed_does_not_overwrite_completed(self, db_session: Session):
        """mark_completed should not overwrite an already completed run."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.completed,
            "parsed_result": {"original": "data"},
            "end_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
        })
        original_end_time = run.end_time
        
        result = crud.mark_completed(run.id, {"new": "data"})
        
        assert result.parsed_result == {"original": "data"}
        
        db_session.delete(run)
        db_session.commit()

    def test_mark_failed_does_not_overwrite_completed(self, db_session: Session):
        """mark_failed should not overwrite an already completed run."""
        crud = AIParsingResultCRUD(db_session)
        
        run = crud.create_item({
            "file_id": 999,
            "status": FileParsingStatuses.completed,
            "parsed_result": {"original": "data"},
        })
        
        result = crud.mark_failed(run.id, "Should not apply")
        
        assert result.status == FileParsingStatuses.completed
        assert result.error_message is None
        
        db_session.delete(run)
        db_session.commit()

    def test_is_terminal_state(self, db_session: Session):
        """is_terminal_state should correctly identify terminal states."""
        crud = AIParsingResultCRUD(db_session)
        
        assert crud.is_terminal_state(FileParsingStatuses.completed) is True
        assert crud.is_terminal_state(FileParsingStatuses.processing_failed) is True
        assert crud.is_terminal_state(FileParsingStatuses.processing_start_failed) is True
        assert crud.is_terminal_state(FileParsingStatuses.processing_timeout) is True
        assert crud.is_terminal_state(FileParsingStatuses.unprocessable_file) is True
        
        assert crud.is_terminal_state(FileParsingStatuses.queued) is False
        assert crud.is_terminal_state(FileParsingStatuses.processing) is False
        assert crud.is_terminal_state(FileParsingStatuses.not_started) is False
