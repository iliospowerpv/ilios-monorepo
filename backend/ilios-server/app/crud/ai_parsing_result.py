from typing import List, Optional

from sqlalchemy import desc

from app.crud.base_crud import BaseCRUD
from app.models.file import AIParsingResult, FileParsingStatuses


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
