from datetime import datetime, timezone
from typing import List, Optional, Tuple
import os
import logging

from sqlalchemy import desc, and_
from sqlalchemy.exc import IntegrityError

from app.crud.base_crud import BaseCRUD
from app.models.file import AIParsingResult, FileParsingStatuses

logger = logging.getLogger(__name__)


class AIParsingResultCRUD(BaseCRUD):
    """CRUD operations on AIParsingResult model."""

    def __init__(self, db_session):
        super().__init__(model=AIParsingResult, db_session=db_session)

    def get_runs_for_file(self, file_id: int) -> List[AIParsingResult]:
        """Get all parse runs for a file, ordered by extraction_run_number DESC."""
        return self.db_session.query(self.model).filter(
            self.model.file_id == file_id
        ).order_by(desc(self.model.extraction_run_number)).all()

    def get_latest_run_for_file(self, file_id: int) -> Optional[AIParsingResult]:
        """Get the most recent parse run for a file."""
        return self.db_session.query(self.model).filter(
            self.model.file_id == file_id
        ).order_by(desc(self.model.extraction_run_number)).first()

    def get_completed_runs_for_file(self, file_id: int) -> List[AIParsingResult]:
        """Get all completed parse runs for a file."""
        return self.db_session.query(self.model).filter(
            self.model.file_id == file_id,
            self.model.status == FileParsingStatuses.completed,
        ).order_by(desc(self.model.extraction_run_number)).all()

    def get_run_by_id(self, run_id: int) -> Optional[AIParsingResult]:
        """Get a specific parse run by ID."""
        return self.get_by_id(run_id)

    def count_runs_for_file(self, file_id: int) -> int:
        """Count total runs for a file."""
        return self.db_session.query(self.model).filter(
            self.model.file_id == file_id
        ).count()

    def create_or_get_active(
        self,
        file_id: int,
        payload: dict,
    ) -> Tuple[AIParsingResult, bool]:
        """Create a new run or return existing active run (idempotent).
        
        Uses database unique constraint to prevent race conditions.
        If a concurrent request already created a run, returns that one.
        
        Returns:
            Tuple of (run, is_new). is_new=True if created, False if existing.
        """
        existing = self.find_active_run(
            file_id=file_id,
            document_type_id=payload.get("document_type_id"),
            schema_version_id=payload.get("schema_version_id"),
            prompt_template_id=payload.get("prompt_template_id"),
        )
        if existing:
            return (existing, False)
        
        try:
            new_run = self.create_item(payload)
            return (new_run, True)
        except IntegrityError as e:
            self.db_session.rollback()
            logger.info(f"Concurrent create detected for file {file_id}, fetching existing run")
            existing = self.find_active_run(
                file_id=file_id,
                document_type_id=payload.get("document_type_id"),
                schema_version_id=payload.get("schema_version_id"),
                prompt_template_id=payload.get("prompt_template_id"),
            )
            if existing:
                return (existing, False)
            raise

    def find_active_run(
        self,
        file_id: int,
        document_type_id: Optional[int] = None,
        schema_version_id: Optional[int] = None,
        prompt_template_id: Optional[int] = None,
    ) -> Optional[AIParsingResult]:
        """Find an existing queued or processing run for the same extraction context.
        
        Used for idempotency: returns existing run instead of creating duplicate.
        """
        active_statuses = [FileParsingStatuses.queued, FileParsingStatuses.processing]
        
        query = self.db_session.query(self.model).filter(
            self.model.file_id == file_id,
            self.model.status.in_(active_statuses),
        )
        
        if document_type_id is not None:
            query = query.filter(self.model.document_type_id == document_type_id)
        if schema_version_id is not None:
            query = query.filter(self.model.schema_version_id == schema_version_id)
        if prompt_template_id is not None:
            query = query.filter(self.model.prompt_template_id == prompt_template_id)
        
        return query.order_by(desc(self.model.id)).first()

    def atomic_claim(
        self,
        run_id: int,
        correlation_id: str,
        worker_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[AIParsingResult]]:
        """Atomically claim a queued run for processing.
        
        Uses row-level locking (SELECT ... FOR UPDATE) to prevent race conditions.
        Only succeeds if status is 'queued' and not already claimed.
        
        Returns:
            Tuple of (success, run). If success=False, run may be the existing
            processing run (already claimed by another worker).
        """
        if worker_id is None:
            worker_id = f"worker-{os.getpid()}"
        
        run = self.db_session.query(self.model).filter(
            self.model.id == run_id
        ).with_for_update(nowait=False).first()
        
        if not run:
            return (False, None)
        
        if run.status != FileParsingStatuses.queued:
            return (False, run)
        
        now = datetime.now(timezone.utc)
        run.status = FileParsingStatuses.processing
        run.claimed_at = now
        run.start_time = now
        run.worker_id = worker_id
        run.correlation_id = correlation_id
        
        self.db_session.commit()
        self.db_session.refresh(run)
        
        return (True, run)

    def is_terminal_state(self, status: FileParsingStatuses) -> bool:
        """Check if a status is a terminal (final) state."""
        terminal_states = [
            FileParsingStatuses.completed,
            FileParsingStatuses.processing_failed,
            FileParsingStatuses.processing_start_failed,
            FileParsingStatuses.processing_timeout,
            FileParsingStatuses.unprocessable_file,
        ]
        return status in terminal_states

    def mark_completed(self, run_id: int, parsed_result: dict, raw_response: str = None) -> Optional[AIParsingResult]:
        """Mark a run as completed with results. Sets end_time."""
        run = self.get_by_id(run_id)
        if not run:
            return None
        
        if self.is_terminal_state(run.status) and run.status == FileParsingStatuses.completed:
            return run
        
        run.status = FileParsingStatuses.completed
        run.parsed_result = parsed_result
        run.end_time = datetime.now(timezone.utc)
        if raw_response:
            run.raw_llm_response = raw_response
        
        self.db_session.commit()
        self.db_session.refresh(run)
        return run

    def mark_failed(self, run_id: int, error_message: str, retries: int = 0) -> Optional[AIParsingResult]:
        """Mark a run as failed with error. Sets end_time."""
        run = self.get_by_id(run_id)
        if not run:
            return None
        
        if self.is_terminal_state(run.status) and run.status == FileParsingStatuses.completed:
            return run
        
        run.status = FileParsingStatuses.processing_failed
        run.error_message = error_message[:500] if error_message else None
        run.end_time = datetime.now(timezone.utc)
        run.retries = retries
        
        self.db_session.commit()
        self.db_session.refresh(run)
        return run
