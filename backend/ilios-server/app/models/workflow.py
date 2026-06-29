"""Workflow Engine DB models (ADDITIVE metadata only).

The Workflow Engine persists ONLY the progress of a guided wizard run — never business
truth. Operational truth keeps flowing through the existing domain tables/endpoints; these
two tables track collected inputs, validation/execution state, and links (by id) to the
domain entity + audit row that an executed write step produced via an EXISTING endpoint.

No operational-truth table is modified or referenced as a source of truth here:
``workflow_step_states`` references a produced entity by ``result_entity_id`` only — it never
stores or becomes the authoritative copy of a fact, baseline, mapping, or company.
"""
import enum

from sqlalchemy import (
    VARCHAR,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from app.db.base_class import Base
from app.models.helpers import utcnow

WORKFLOW_RUN_STATUS_ENUM_NAME = "workflow_run_status_enum"
WORKFLOW_STEP_STATUS_ENUM_NAME = "workflow_step_status_enum"


class WorkflowRunStatus(enum.Enum):
    """Lifecycle of a single wizard run."""

    active = "active"
    paused = "paused"
    completed = "completed"
    abandoned = "abandoned"


class WorkflowStepStatus(enum.Enum):
    """Server-side validation state of a single step's collected inputs."""

    pending = "pending"
    valid = "valid"
    invalid = "invalid"


class WorkflowRun(Base):
    """One in-progress/completed run of a workflow definition for a single user."""

    __tablename__ = "workflow_runs"

    __table_args__ = (
        Index("ix_workflow_runs_user_id", "user_id"),
        Index("ix_workflow_runs_workflow_id", "workflow_id"),
        Index("ix_workflow_runs_status", "status"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)

    # Definition identity. A run binds to a (workflow_id, workflow_version) so a resumed run
    # can be re-validated rather than blindly replayed if the definition changed.
    workflow_id = Column(VARCHAR, nullable=False)
    workflow_version = Column(VARCHAR, nullable=False)

    # The run executes strictly as the logged-in user.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Optional scope; null when the run itself creates the scoping entity (e.g. add_company).
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="SET NULL"), nullable=True)

    status = Column(
        Enum(WorkflowRunStatus, name=WORKFLOW_RUN_STATUS_ENUM_NAME),
        nullable=False,
        default=WorkflowRunStatus.active,
        server_default=WorkflowRunStatus.active.value,
    )
    current_step = Column(VARCHAR, nullable=True)
    resume_token = Column(VARCHAR, nullable=True, unique=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    step_states = relationship(
        "WorkflowStepState",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="WorkflowStepState.id",
    )


class WorkflowStepState(Base):
    """Per-step record of collected inputs, validation, and (for a write) execution result.

    ``result_entity_id`` / ``audit_log_id`` reference the domain entity and audit row that the
    EXISTING endpoint produced — this row never stores the authoritative copy of business
    truth, and the ``executed`` flag + ``idempotency_key`` prevent double execution on
    resume/retry.
    """

    __tablename__ = "workflow_step_states"

    __table_args__ = (
        UniqueConstraint("run_id", "step_id", name="uq_workflow_step_states_run_id_step_id"),
        UniqueConstraint("idempotency_key", name="uq_workflow_step_states_idempotency_key"),
        Index("ix_workflow_step_states_run_id", "run_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)

    run_id = Column(Integer, ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    step_id = Column(VARCHAR, nullable=False)

    # Wizard "draft" inputs — SEPARATE from any domain draft state (candidate facts, draft
    # baselines). Never a substitute for a real mutation.
    inputs = Column(JSONB, nullable=True)
    validation_status = Column(
        Enum(WorkflowStepStatus, name=WORKFLOW_STEP_STATUS_ENUM_NAME),
        nullable=False,
        default=WorkflowStepStatus.pending,
        server_default=WorkflowStepStatus.pending.value,
    )
    validation_errors = Column(JSONB, nullable=True)

    executed = Column(
        Boolean, nullable=False, default=False, server_default=expression.false()
    )
    idempotency_key = Column(VARCHAR, nullable=True)

    result_entity_type = Column(VARCHAR, nullable=True)
    result_entity_id = Column(Integer, nullable=True)
    audit_log_id = Column(Integer, ForeignKey("audit_logs.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    run = relationship("WorkflowRun", back_populates="step_states")
