"""Declarative workflow definitions for the native Workflow Engine.

A workflow is DATA: an ordered list of steps, each with inputs, a confirmation policy, and
(for write steps) a backing executor that invokes an EXISTING endpoint/service. The engine
orchestrates collection/validation/confirmation/execution; it never owns business truth.

Governance invariants are enforced at LOAD TIME by ``validate_definition`` (run for every
registered workflow when this module is imported): a governed step can never skip
confirmation or auto-execute, and no write step may use ``confirmation='none'`` or
``auto_execute=True``. Importing this module with an invalid definition raises immediately,
making "no silent mutation of operational truth" structurally true.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel

from app.models.site import State
from app.schema.company import CreateCompanySchema
from app.static.companies import CompanyTypes

# --- Confirmation tiers (audit §7) ----------------------------------------------------

CONFIRMATION_NONE = "none"
CONFIRMATION_STANDARD = "standard"
CONFIRMATION_GOVERNED = "governed"

# --- Step kinds -----------------------------------------------------------------------

STEP_COLLECT = "collect"  # read-only input collection (NO side effect)
STEP_EXECUTE = "execute"  # write step (invokes an existing endpoint behind confirm)


@dataclass(frozen=True)
class FieldDef:
    name: str
    label: str
    type: str = "text"  # text | email | tel | select | textarea
    required: bool = False
    options_source: Optional[str] = None  # resolved to options[] at serialization time
    placeholder: Optional[str] = None
    help: Optional[str] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None


@dataclass(frozen=True)
class StepDef:
    id: str
    title: str
    kind: str
    confirmation: str
    inputs: tuple[FieldDef, ...] = ()
    help: Optional[str] = None
    required_permission: Optional[str] = None
    governed: bool = False
    # An explicit "skip the human" knob. It exists ONLY so the loader can structurally reject
    # it; the engine has no auto-execute path at all (every write requires a human confirm).
    auto_execute: bool = False
    audit_action: Optional[str] = None


@dataclass(frozen=True)
class WorkflowDef:
    id: str
    version: str
    title: str
    description: str
    entry_permission: str
    steps: tuple[StepDef, ...]
    # workflow_id key into the executor registry resolved at execute time.
    payload_schema_key: Optional[str] = None


class WorkflowDefinitionError(RuntimeError):
    """Raised at load time when a definition violates a governance/structural invariant."""


def validate_definition(wf: WorkflowDef) -> None:
    """Fail-closed structural + governance validation, executed at import time."""
    if not wf.steps:
        raise WorkflowDefinitionError(f"workflow '{wf.id}' has no steps")

    seen: set[str] = set()
    for step in wf.steps:
        if step.id in seen:
            raise WorkflowDefinitionError(f"workflow '{wf.id}' has duplicate step '{step.id}'")
        seen.add(step.id)

        if step.kind not in (STEP_COLLECT, STEP_EXECUTE):
            raise WorkflowDefinitionError(f"step '{step.id}' has unknown kind '{step.kind}'")
        if step.confirmation not in (
            CONFIRMATION_NONE,
            CONFIRMATION_STANDARD,
            CONFIRMATION_GOVERNED,
        ):
            raise WorkflowDefinitionError(
                f"step '{step.id}' has unknown confirmation '{step.confirmation}'"
            )

        # ABSOLUTE governance rule (audit §7/§9): a governed step can never auto-execute or
        # skip confirmation.
        if step.governed:
            if step.auto_execute:
                raise WorkflowDefinitionError(
                    f"governed step '{step.id}' must not set auto_execute=True"
                )
            if step.confirmation != CONFIRMATION_GOVERNED:
                raise WorkflowDefinitionError(
                    f"governed step '{step.id}' must use confirmation='governed'"
                )

        # Every write step requires an explicit human confirmation; there is no auto path.
        if step.kind == STEP_EXECUTE:
            if step.confirmation == CONFIRMATION_NONE:
                raise WorkflowDefinitionError(
                    f"write step '{step.id}' must not use confirmation='none'"
                )
            if step.auto_execute:
                raise WorkflowDefinitionError(
                    f"write step '{step.id}' must not set auto_execute=True (human confirm required)"
                )
        elif step.confirmation != CONFIRMATION_NONE:
            # Read-only collection steps never carry a confirmation tier.
            raise WorkflowDefinitionError(
                f"collect step '{step.id}' must use confirmation='none'"
            )


# --- Pilot workflow: Add Company ------------------------------------------------------

ADD_COMPANY = WorkflowDef(
    id="add_company",
    version="1",
    title="Add Company",
    description="Create a new company and grant yourself company-admin membership.",
    entry_permission="platform_admin",
    payload_schema_key="add_company",
    steps=(
        StepDef(
            id="company_details",
            title="Company details",
            kind=STEP_COLLECT,
            confirmation=CONFIRMATION_NONE,
            help="Enter the company's name, type, and address.",
            required_permission="platform_admin",
            inputs=(
                FieldDef(
                    "name",
                    "Company name",
                    "text",
                    required=True,
                    max_length=100,
                    placeholder="Green Lantern",
                ),
                FieldDef(
                    "company_type",
                    "Company type",
                    "select",
                    required=True,
                    options_source="company_types",
                ),
                FieldDef(
                    "address",
                    "Address",
                    "text",
                    required=True,
                    max_length=255,
                    placeholder="719 Main Street",
                ),
                FieldDef("city", "City", "text", required=True, max_length=100),
                FieldDef(
                    "state", "State", "select", required=True, options_source="us_states"
                ),
                FieldDef(
                    "zip_code",
                    "ZIP code",
                    "text",
                    required=True,
                    max_length=5,
                    pattern=r"^[0-9]+$",
                    placeholder="08062",
                ),
                FieldDef("county", "County", "text", required=False, max_length=100),
                FieldDef("email", "Email", "email", required=False, max_length=100),
                FieldDef(
                    "phone",
                    "Phone",
                    "tel",
                    required=False,
                    help="10 digits (US).",
                ),
            ),
        ),
        StepDef(
            id="review_and_create",
            title="Review & create",
            kind=STEP_EXECUTE,
            confirmation=CONFIRMATION_STANDARD,
            help="Review the details, then create the company.",
            required_permission="platform_admin",
            audit_action="workflow.add_company.execute",
        ),
    ),
)


REGISTRY: dict[str, WorkflowDef] = {ADD_COMPANY.id: ADD_COMPANY}

# Validate every registered definition at import time (fail-closed).
for _wf in REGISTRY.values():
    validate_definition(_wf)


# --- Lookups --------------------------------------------------------------------------


def get_definition(workflow_id: str) -> Optional[WorkflowDef]:
    return REGISTRY.get(workflow_id)


def get_step(wf: WorkflowDef, step_id: str) -> Optional[StepDef]:
    for step in wf.steps:
        if step.id == step_id:
            return step
    return None


def first_step_id(wf: WorkflowDef) -> Optional[str]:
    return wf.steps[0].id if wf.steps else None


def resolve_options(options_source: Optional[str]) -> Optional[list[dict]]:
    """Resolve a select field's ``options_source`` to concrete {label, value} options."""
    if options_source is None:
        return None
    if options_source == "company_types":
        return [{"label": ct.value, "value": ct.value} for ct in CompanyTypes]
    if options_source == "us_states":
        return [{"label": st.value, "value": st.value} for st in State]
    return []


# Per-(workflow, step) server validator for a COLLECT step's inputs. Reused to validate a
# saved step (best-effort, non-blocking) and is the SAME schema the real endpoint enforces.
STEP_INPUT_SCHEMAS: dict[tuple[str, str], type[BaseModel]] = {
    ("add_company", "company_details"): CreateCompanySchema,
}

# Per-workflow payload schema used to validate the merged inputs of a write step before it is
# dispatched to the existing endpoint. This is the EXISTING domain schema, not a new one.
WORKFLOW_PAYLOAD_SCHEMAS: dict[str, type[BaseModel]] = {
    "add_company": CreateCompanySchema,
}


def get_step_input_schema(workflow_id: str, step_id: str) -> Optional[type[BaseModel]]:
    return STEP_INPUT_SCHEMAS.get((workflow_id, step_id))


def get_payload_schema(workflow_id: str) -> Optional[type[BaseModel]]:
    return WORKFLOW_PAYLOAD_SCHEMAS.get(workflow_id)
