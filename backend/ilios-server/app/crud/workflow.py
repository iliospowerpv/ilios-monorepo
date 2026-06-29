"""CRUD for the Workflow Engine run/step tables."""
from typing import Optional, Sequence

from app.crud.base_crud import BaseCRUD
from app.models.workflow import WorkflowRun, WorkflowRunStatus, WorkflowStepState


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

    def list_for_user(
        self,
        user_id: int,
        *,
        statuses: Optional[Sequence[WorkflowRunStatus]] = None,
        workflow_id: Optional[str] = None,
        sequence_id: Optional[str] = None,
        parent_run_id: Optional[int] = None,
        limit: int = 100,
    ) -> list[WorkflowRun]:
        """List a single user's runs (owner-scoped, fail-closed), newest activity first.

        Always filtered to ``user_id`` so one user can never enumerate another's runs.
        Optional filters narrow by status set, workflow, orchestration sequence, or parent
        run. ``limit`` is capped by the caller (router) to bound the result set.
        """
        query = self.db_session.query(self.model).filter(self.model.user_id == user_id)
        if statuses:
            query = query.filter(self.model.status.in_(list(statuses)))
        if workflow_id:
            query = query.filter(self.model.workflow_id == workflow_id)
        if sequence_id:
            query = query.filter(self.model.sequence_id == sequence_id)
        if parent_run_id is not None:
            query = query.filter(self.model.parent_run_id == parent_run_id)
        return (
            query.order_by(self.model.updated_at.desc(), self.model.id.desc())
            .limit(limit)
            .all()
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
