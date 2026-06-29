"""CRUD for the Workflow Engine run/step tables."""
from typing import Optional

from app.crud.base_crud import BaseCRUD
from app.models.workflow import WorkflowRun, WorkflowStepState


class WorkflowRunCRUD(BaseCRUD):
    """CRUD operations on the WorkflowRun model."""

    def __init__(self, db_session):
        super().__init__(model=WorkflowRun, db_session=db_session)

    def get_for_user(self, run_id: int, user_id: int) -> Optional[WorkflowRun]:
        """Fetch a run owned by the given user (multi-tenant isolation, fail-closed)."""
        return (
            self.db_session.query(self.model)
            .filter(self.model.id == run_id, self.model.user_id == user_id)
            .first()
        )


class WorkflowStepStateCRUD(BaseCRUD):
    """CRUD operations on the WorkflowStepState model."""

    def __init__(self, db_session):
        super().__init__(model=WorkflowStepState, db_session=db_session)

    def get_run_step(self, run_id: int, step_id: str) -> Optional[WorkflowStepState]:
        return (
            self.db_session.query(self.model)
            .filter(self.model.run_id == run_id, self.model.step_id == step_id)
            .first()
        )

    def list_for_run(self, run_id: int) -> list[WorkflowStepState]:
        return (
            self.db_session.query(self.model)
            .filter(self.model.run_id == run_id)
            .order_by(self.model.id)
            .all()
        )

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[WorkflowStepState]:
        return (
            self.db_session.query(self.model)
            .filter(self.model.idempotency_key == idempotency_key)
            .first()
        )
