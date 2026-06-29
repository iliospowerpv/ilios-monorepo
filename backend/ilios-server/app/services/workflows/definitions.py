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

from pydantic import BaseModel, EmailStr, Field

from app.models.site import State
from app.schema.company import CreateCompanySchema
from app.schema.site import CreateSiteSchema
from app.schema.user_company_access import CompanyRoleEnum
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
    type: str = "text"  # text | email | tel | number | select | textarea
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
    # Name of the multipart file part this EXECUTE step expects (e.g. "file"). When set, the
    # step is executed via the dedicated multipart route (POST .../execute-file) so the raw
    # bytes travel as a real upload and are NEVER persisted in the run's JSONB inputs. The
    # JSON targets (e.g. site_id/document_id) are still collected/validated/previewed normally.
    multipart_file_field: Optional[str] = None


@dataclass(frozen=True)
class PrerequisiteDef:
    """A declarative, read-only precondition advertised for a workflow.

    Prerequisites are NOT authorization (entry_permission stays the authoritative gate). They
    are user-facing guidance: the dashboard evaluates each via a pure-read evaluator and, when
    unmet, shows the workflow as blocked with ``unmet_message`` so the user knows what to do
    first. An unmet prerequisite never silently grants or denies access — it only informs.
    """

    key: str
    label: str
    unmet_message: str
    # Key into the engine's read-only PREREQUISITE_EVALUATORS registry. Validated at engine
    # import time so a typo'd evaluator key fails closed (treated as unmet) rather than crashing.
    evaluator_key: str


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
    # User-facing copy returned by the engine on successful execution. Falls back to a generic
    # message when unset, so the engine never hardcodes per-workflow copy.
    success_message: Optional[str] = None
    # --- Discovery / registry metadata (ADDITIVE; powers the dashboard + orchestrator) ---
    # Purely presentational/declarative — none of these grant access or trigger execution.
    category: str = "General"
    icon: Optional[str] = None
    # Workflow ids the dashboard MAY suggest running next. A suggestion is just a hint; the
    # next workflow is always an independent, separately-permissioned run (never auto-started).
    suggested_next: tuple[str, ...] = ()
    # FE deep-link template to the entity a successful run creates ({entity_id} substituted).
    landing_route_template: Optional[str] = None
    # Whether this workflow may appear as a step inside a declarative SequenceDef.
    sequence_eligible: bool = True
    # Declarative, read-only preconditions advertised to the dashboard. NOT authorization —
    # purely informational "do this first" guidance evaluated via pure-read evaluators.
    prerequisites: tuple[PrerequisiteDef, ...] = ()


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
        else:
            if step.confirmation != CONFIRMATION_NONE:
                # Read-only collection steps never carry a confirmation tier.
                raise WorkflowDefinitionError(
                    f"collect step '{step.id}' must use confirmation='none'"
                )
            # A multipart file part is a property of the WRITE step only; a collect step never
            # receives raw bytes (targets are collected as plain JSON).
            if step.multipart_file_field is not None:
                raise WorkflowDefinitionError(
                    f"collect step '{step.id}' must not set multipart_file_field"
                )


# --- Pilot workflow: Add Company ------------------------------------------------------

ADD_COMPANY = WorkflowDef(
    id="add_company",
    version="1",
    title="Add Company",
    description="Create a new company and grant yourself company-admin membership.",
    entry_permission="platform_admin",
    payload_schema_key="add_company",
    success_message="Company created successfully.",
    category="Onboarding",
    icon="business",
    suggested_next=("add_site",),
    landing_route_template="/project-hub/companies/{entity_id}",
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


# --- Pilot 2 workflow: Add Site / Project ---------------------------------------------
#
# Proves the engine generalizes beyond Add Company: a company-scoped permission model
# (assets_management:create_site, NOT platform_admin) and a DYNAMIC select (the company
# picker). The single collect step holds the full CreateSiteSchema; the execute step dispatches
# to the EXISTING site-create endpoint behind a standard confirmation. Per replit.md the backend
# entity stays "Site" — only the user-facing labels read "Project".

ADD_SITE = WorkflowDef(
    id="add_site",
    version="1",
    title="Add Project",
    description="Create a new project (site) within a company you manage.",
    entry_permission="assets_management:create_site",
    payload_schema_key="add_site",
    success_message="Project created successfully.",
    category="Onboarding",
    icon="solar_power",
    landing_route_template="/project-hub/projects/{entity_id}",
    steps=(
        StepDef(
            id="project_details",
            title="Project details",
            kind=STEP_COLLECT,
            confirmation=CONFIRMATION_NONE,
            help="Choose the company, then enter the project's location and system details.",
            required_permission="assets_management:create_site",
            inputs=(
                FieldDef(
                    "company_id",
                    "Company",
                    "select",
                    required=True,
                    options_source="companies",
                    help="The company that will own this project.",
                ),
                FieldDef("name", "Project name", "text", required=True, placeholder="Apollo"),
                FieldDef(
                    "address",
                    "Address",
                    "text",
                    required=True,
                    placeholder="719 Main Street",
                ),
                FieldDef("city", "City", "text", required=True),
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
                FieldDef("county", "County", "text", required=False),
                FieldDef(
                    "system_size_ac",
                    "System size AC (kW)",
                    "number",
                    required=True,
                    placeholder="1000",
                ),
                FieldDef(
                    "system_size_dc",
                    "System size DC (kW)",
                    "number",
                    required=True,
                    placeholder="1200",
                ),
                FieldDef(
                    "lon_lat_url",
                    "Coordinates",
                    "text",
                    required=True,
                    help="Latitude/longitude or a map URL for the site.",
                    placeholder="41.9486, -72.6443",
                ),
                FieldDef(
                    "timezone",
                    "Timezone",
                    "select",
                    required=True,
                    options_source="us_timezones",
                    help="Used for site-local daily production boundaries.",
                ),
            ),
        ),
        StepDef(
            id="review_and_create",
            title="Review & create",
            kind=STEP_EXECUTE,
            confirmation=CONFIRMATION_STANDARD,
            help="Review the details, then create the project.",
            required_permission="assets_management:create_site",
            audit_action="workflow.add_site.execute",
        ),
    ),
)


# --- Workflow: Invite User ------------------------------------------------------------
#
# Create-or-reuse a user account and grant them membership to a company. A SINGLE thin
# executor reuses the EXISTING create-user endpoint (POST /users/, global-admin scoped) and the
# EXISTING add-company-member endpoint; it is idempotent (an already-existing email/membership
# is reused, not duplicated). entry_permission is platform_admin because create_user requires a
# global admin — matching the existing manual user-creation surface.

INVITE_USER = WorkflowDef(
    id="invite_user",
    version="1",
    title="Invite User",
    description="Create (or reuse) a user account and grant them membership to a company.",
    entry_permission="platform_admin",
    payload_schema_key="invite_user",
    success_message="User invited and granted company membership.",
    category="Onboarding",
    icon="person_add",
    steps=(
        StepDef(
            id="invitee_details",
            title="Invitee details",
            kind=STEP_COLLECT,
            confirmation=CONFIRMATION_NONE,
            help="Enter the person's details and choose the company and role to grant.",
            required_permission="platform_admin",
            inputs=(
                FieldDef("first_name", "First name", "text", required=True, max_length=100),
                FieldDef("last_name", "Last name", "text", required=True, max_length=100),
                FieldDef("email", "Email", "email", required=True, max_length=100),
                FieldDef(
                    "phone",
                    "Phone",
                    "tel",
                    required=True,
                    help="10 digits (US).",
                    placeholder="0123456789",
                ),
                FieldDef(
                    "company_id",
                    "Company",
                    "select",
                    required=True,
                    options_source="membership_companies",
                    help="The company to grant membership in.",
                ),
                FieldDef(
                    "role",
                    "Company role",
                    "select",
                    required=True,
                    options_source="membership_roles",
                ),
            ),
        ),
        StepDef(
            id="review_and_invite",
            title="Review & invite",
            kind=STEP_EXECUTE,
            confirmation=CONFIRMATION_STANDARD,
            help="Review the details, then create the user and grant company membership.",
            required_permission="platform_admin",
            audit_action="workflow.invite_user.execute",
        ),
    ),
)


# --- Workflow: Document Upload --------------------------------------------------------
#
# Upload a document file into a project's data room. The JSON targets (project + document slot)
# are collected/validated/previewed like any other workflow; the file bytes travel via the
# dedicated multipart route (declared by multipart_file_field) so they are NEVER stored in the
# run's JSONB inputs. The executor reuses the EXISTING upload endpoint verbatim.

DOCUMENT_UPLOAD = WorkflowDef(
    id="document_upload",
    version="1",
    title="Upload Document",
    description="Upload a document file into a project's data room.",
    entry_permission="diligence:edit",
    payload_schema_key="document_upload",
    success_message="File uploaded successfully.",
    category="Data Room",
    icon="upload_file",
    prerequisites=(
        PrerequisiteDef(
            key="has_accessible_project",
            label="You can access at least one project",
            unmet_message="You need access to a project before you can upload documents.",
            evaluator_key="has_accessible_project",
        ),
    ),
    steps=(
        StepDef(
            id="select_target",
            title="Select destination",
            kind=STEP_COLLECT,
            confirmation=CONFIRMATION_NONE,
            help="Choose the project and the document slot to upload into.",
            required_permission="diligence:edit",
            inputs=(
                FieldDef(
                    "site_id",
                    "Project",
                    "select",
                    required=True,
                    options_source="accessible_projects",
                ),
                FieldDef(
                    "document_id",
                    "Document",
                    "select",
                    required=True,
                    options_source="project_documents",
                    help="Document slot within the selected project.",
                ),
            ),
        ),
        StepDef(
            id="upload",
            title="Upload file",
            kind=STEP_EXECUTE,
            confirmation=CONFIRMATION_STANDARD,
            help="Pick a file, review the destination, then upload.",
            required_permission="diligence:edit",
            audit_action="workflow.document_upload.execute",
            multipart_file_field="file",
        ),
    ),
)


# --- Workflow: Parse Document --------------------------------------------------------
#
# Trigger in-app AI parsing on an already-uploaded document file. The workflow only SELECTS the
# target file (project -> document -> file cascade) and dispatches to the EXISTING parsing
# endpoint; the engine never performs AI work itself. Parsing runs asynchronously (202): the
# returned ai_parsing_run id is the honest result the user can track in the Data Room.

PARSE_DOCUMENT = WorkflowDef(
    id="parse_document",
    version="1",
    title="Parse Document",
    description="Trigger in-app AI parsing on an uploaded document file.",
    entry_permission="diligence:edit",
    payload_schema_key="parse_document",
    success_message="AI parsing started for this file.",
    category="Data Room",
    icon="document_scanner",
    prerequisites=(
        PrerequisiteDef(
            key="has_accessible_project",
            label="You can access at least one project",
            unmet_message="You need access to a project before you can parse documents.",
            evaluator_key="has_accessible_project",
        ),
        PrerequisiteDef(
            key="has_uploaded_file",
            label="At least one document file has been uploaded",
            unmet_message="Upload a document file first, then you can run AI parsing on it.",
            evaluator_key="has_uploaded_file",
        ),
    ),
    steps=(
        StepDef(
            id="select_file",
            title="Select file",
            kind=STEP_COLLECT,
            confirmation=CONFIRMATION_NONE,
            help="Choose the project, document, and file to parse.",
            required_permission="diligence:edit",
            inputs=(
                FieldDef(
                    "site_id",
                    "Project",
                    "select",
                    required=True,
                    options_source="accessible_projects",
                ),
                FieldDef(
                    "document_id",
                    "Document",
                    "select",
                    required=True,
                    options_source="project_documents",
                ),
                FieldDef(
                    "file_id",
                    "File",
                    "select",
                    required=True,
                    options_source="document_files",
                ),
            ),
        ),
        StepDef(
            id="trigger_parse",
            title="Trigger parsing",
            kind=STEP_EXECUTE,
            confirmation=CONFIRMATION_STANDARD,
            help="Review the file, then start AI parsing.",
            required_permission="diligence:edit",
            audit_action="workflow.parse_document.execute",
        ),
    ),
)


REGISTRY: dict[str, WorkflowDef] = {
    ADD_COMPANY.id: ADD_COMPANY,
    ADD_SITE.id: ADD_SITE,
    INVITE_USER.id: INVITE_USER,
    DOCUMENT_UPLOAD.id: DOCUMENT_UPLOAD,
    PARSE_DOCUMENT.id: PARSE_DOCUMENT,
}

# Validate every registered definition at import time (fail-closed).
for _wf in REGISTRY.values():
    validate_definition(_wf)


# --- Declarative orchestrator sequences ----------------------------------------------
# A SequenceDef chains otherwise-INDEPENDENT workflows into one guided multi-workflow journey
# (e.g. onboarding: add a company, then its first project). The orchestrator NEVER executes
# anything itself — each step is a normal, independently-permissioned workflow run. The
# sequence only declares ordering so a user can flow through end to end and resume across
# sessions (persisted via workflow_runs.sequence_id / sequence_step_index / parent_run_id).


@dataclass(frozen=True)
class PrefillHint:
    """A DECLARATIVE, best-effort cross-step prefill hint for the FE sequence runner.

    It says: "when you reach this step, seed its collect field ``target_field`` with the entity
    id that an EARLIER sequence step (``from_step_index``) created (that step's
    ``result_entity_id``)." This carries NO executable logic and grants NO access — the FE runner
    applies it best-effort (only when the value is a valid option for the target field) and every
    underlying workflow still validates + authorizes its own inputs at execute time. It exists so
    a guided sequence can chain (company -> its site, site -> its upload) without re-typing ids.
    """

    target_field: str
    from_step_index: int


@dataclass(frozen=True)
class SequenceStepDef:
    workflow_id: str
    title: str
    description: str
    # Declarative prefill hints applied by the FE runner (best-effort, never authoritative).
    prefill: tuple[PrefillHint, ...] = ()


@dataclass(frozen=True)
class SequenceDef:
    id: str
    title: str
    description: str
    category: str
    steps: tuple[SequenceStepDef, ...]
    icon: Optional[str] = None


def validate_sequence(seq: SequenceDef) -> None:
    """Fail-closed: a sequence must have steps, every step must name a real sequence-eligible
    workflow, and every prefill hint must reference a strictly EARLIER step + a non-empty field."""
    if not seq.steps:
        raise WorkflowDefinitionError(f"sequence '{seq.id}' has no steps")
    for idx, step in enumerate(seq.steps):
        wf = REGISTRY.get(step.workflow_id)
        if wf is None:
            raise WorkflowDefinitionError(
                f"sequence '{seq.id}' references unknown workflow '{step.workflow_id}'"
            )
        if not wf.sequence_eligible:
            raise WorkflowDefinitionError(
                f"sequence '{seq.id}' uses workflow '{step.workflow_id}' which is not sequence-eligible"
            )
        for hint in step.prefill:
            if not hint.target_field:
                raise WorkflowDefinitionError(
                    f"sequence '{seq.id}' step {idx} has a prefill hint with no target_field"
                )
            if not (0 <= hint.from_step_index < idx):
                raise WorkflowDefinitionError(
                    f"sequence '{seq.id}' step {idx} prefill references step "
                    f"{hint.from_step_index}, which is not a strictly earlier step"
                )


ONBOARDING_SEQUENCE = SequenceDef(
    id="onboarding",
    title="Onboard a Company & First Project",
    description="Create a company, then add its first project (site) — guided end to end.",
    category="Onboarding",
    icon="rocket_launch",
    steps=(
        SequenceStepDef(
            workflow_id="add_company",
            title="Create the company",
            description="Add the owning company.",
        ),
        SequenceStepDef(
            workflow_id="add_site",
            title="Add the first project",
            description="Create the company's first project (site).",
            # Seed the new site's company from the company created in step 0.
            prefill=(PrefillHint(target_field="company_id", from_step_index=0),),
        ),
    ),
)

# Site data onboarding: stand up a project, then upload a diligence document, then parse it.
# Each step is an independent, separately-permissioned workflow run; the sequence only chains
# them so a user can flow site -> first document -> AI parse end to end.
SITE_DILIGENCE_SEQUENCE = SequenceDef(
    id="site_diligence",
    title="Set Up a Project's Data Room",
    description=(
        "Add a project, upload its first diligence document, then run AI extraction — guided "
        "end to end."
    ),
    category="Onboarding",
    icon="folder_open",
    steps=(
        SequenceStepDef(
            workflow_id="add_site",
            title="Add the project",
            description="Create the project (site) whose Data Room you are setting up.",
        ),
        SequenceStepDef(
            workflow_id="document_upload",
            title="Upload the first document",
            description="Upload a diligence document into the project's Data Room.",
            # Seed the upload target with the project created in step 0.
            prefill=(PrefillHint(target_field="site_id", from_step_index=0),),
        ),
        SequenceStepDef(
            workflow_id="parse_document",
            title="Run AI extraction",
            description="Parse the uploaded document to extract its diligence terms.",
            # Seed the parse target's project from step 0; the document/file are chosen via the
            # project-scoped cascade (they are user selections, not created entities).
            prefill=(PrefillHint(target_field="site_id", from_step_index=0),),
        ),
    ),
)

# Portfolio bootstrap: create a company, its first project, then invite a collaborator to it.
PORTFOLIO_SETUP_SEQUENCE = SequenceDef(
    id="portfolio_setup",
    title="Bootstrap a Portfolio",
    description=(
        "Create a company, add its first project, then invite a teammate to collaborate — guided "
        "end to end."
    ),
    category="Onboarding",
    icon="groups",
    steps=(
        SequenceStepDef(
            workflow_id="add_company",
            title="Create the company",
            description="Add the owning company.",
        ),
        SequenceStepDef(
            workflow_id="add_site",
            title="Add the first project",
            description="Create the company's first project (site).",
            prefill=(PrefillHint(target_field="company_id", from_step_index=0),),
        ),
        SequenceStepDef(
            workflow_id="invite_user",
            title="Invite a teammate",
            description="Invite a collaborator to the new company.",
            # Invite into the company created in step 0 (not the site created in step 1).
            prefill=(PrefillHint(target_field="company_id", from_step_index=0),),
        ),
    ),
)

SEQUENCES: dict[str, SequenceDef] = {
    ONBOARDING_SEQUENCE.id: ONBOARDING_SEQUENCE,
    SITE_DILIGENCE_SEQUENCE.id: SITE_DILIGENCE_SEQUENCE,
    PORTFOLIO_SETUP_SEQUENCE.id: PORTFOLIO_SETUP_SEQUENCE,
}

# Validate every registered sequence at import time (fail-closed).
for _seq in SEQUENCES.values():
    validate_sequence(_seq)


# --- Lookups --------------------------------------------------------------------------


def get_definition(workflow_id: str) -> Optional[WorkflowDef]:
    return REGISTRY.get(workflow_id)


def get_sequence(sequence_id: str) -> Optional["SequenceDef"]:
    return SEQUENCES.get(sequence_id)


def get_step(wf: WorkflowDef, step_id: str) -> Optional[StepDef]:
    for step in wf.steps:
        if step.id == step_id:
            return step
    return None


def first_step_id(wf: WorkflowDef) -> Optional[str]:
    return wf.steps[0].id if wf.steps else None


# Curated IANA timezones covering the platform's US footprint (+ UTC). Values MUST be exact
# IANA names because CreateSiteSchema validates the timezone against zoneinfo. This is a
# wizard-presentation convenience; the underlying schema still accepts any valid IANA value.
_US_TIMEZONES: tuple[tuple[str, str], ...] = (
    ("UTC", "UTC"),
    ("America/New_York", "Eastern (America/New_York)"),
    ("America/Chicago", "Central (America/Chicago)"),
    ("America/Denver", "Mountain (America/Denver)"),
    ("America/Phoenix", "Arizona — no DST (America/Phoenix)"),
    ("America/Los_Angeles", "Pacific (America/Los_Angeles)"),
    ("America/Anchorage", "Alaska (America/Anchorage)"),
    ("Pacific/Honolulu", "Hawaii (Pacific/Honolulu)"),
)


def _editable_company_options(db_session, current_user) -> list[dict]:
    """Companies the user may create a site in: active companies where they hold Asset
    Management 'edit'. Platform-bypass users see all active companies. Best-effort and
    read-only — the existing site-create endpoint remains the authoritative per-company guard.
    """
    from app.models.company import Company
    from app.static.permissions import PermissionsModules

    if getattr(current_user, "has_platform_bypass", False):
        rows = (
            db_session.query(Company.id, Company.name)
            .filter(Company.is_archived.is_(False))
            .order_by(Company.name)
            .all()
        )
        return [{"label": name, "value": str(cid)} for cid, name in rows]

    try:
        company_ids = current_user.get_limited_companies_ids() or []
    except Exception:
        company_ids = []
    if not company_ids:
        return []

    from app.helpers.access_resolver import AccessDecision, resolve_effective_access

    names = {
        c.id: c.name
        for c in db_session.query(Company)
        .filter(Company.id.in_(company_ids), Company.is_archived.is_(False))
        .all()
    }
    module_key = PermissionsModules.assets_management.value
    out: list[dict] = []
    for cid in company_ids:
        name = names.get(cid)
        if name is None:
            continue
        try:
            access = resolve_effective_access(
                user_id=current_user.id, company_id=cid, db_session=db_session
            )
            if access.decision == AccessDecision.ALLOW and "edit" in access.effective_module_permissions.get(
                module_key, set()
            ):
                out.append({"label": name, "value": str(cid)})
        except Exception:
            continue
    out.sort(key=lambda o: o["label"].lower())
    return out


def _ctx_int(context: Optional[dict], key: str) -> Optional[int]:
    """Read an int from the dynamic-options context (collected inputs), tolerating str/None."""
    if not context:
        return None
    raw = context.get(key)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _user_accessible_site_ids(current_user) -> Optional[set[int]]:
    """The site ids a non-bypass user may access, or None for platform-bypass (= all)."""
    if getattr(current_user, "has_platform_bypass", False):
        return None
    try:
        ids = current_user.get_limited_sites_ids()
    except Exception:
        ids = None
    return set(ids) if ids else set()


def _diligence_editable_site_ids(db_session, current_user) -> Optional[set[int]]:
    """Site ids on which the user has Diligence ``edit`` (company- OR project-level grant), or
    ``None`` for platform-bypass (= all non-archived sites).

    Site VISIBILITY is NOT sufficient: the Data Room list/upload/parse endpoints all enforce the
    Diligence module permission per document/file, so these option/prerequisite reads must mirror
    that guard or they would leak project/document/file metadata for a project the user can merely
    see but cannot open in the Data Room. We scope to ``edit`` (not ``view``) because every
    consumer of this set drives an upload/parse action that itself requires Diligence ``edit``;
    ``edit`` is strictly tighter than ``view`` (the resolver normalizes ``edit`` to include
    ``view``), so this fully closes the disclosure while never showing a dead-end project. The
    underlying endpoints remain the authoritative per-document guard at execute time. Fail-closed:
    any error excludes the site rather than exposing it.
    """
    if getattr(current_user, "has_platform_bypass", False):
        return None
    candidate = _user_accessible_site_ids(current_user)
    if not candidate:
        return set()
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        return set()
    from app.helpers.permission_guards import require_module_permission
    from app.models.site import Site
    from app.static.permissions import PermissionsModules

    rows = (
        db_session.query(Site.id, Site.company_id)
        .filter(Site.id.in_(list(candidate)), Site.is_archived.is_(False))
        .all()
    )
    editable: set[int] = set()
    for sid, cid in rows:
        if cid is None:
            continue
        try:
            require_module_permission(
                user_id=user_id,
                company_id=cid,
                db_session=db_session,
                module_key=PermissionsModules.diligence.value,
                action="edit",
                project_id=sid,
            )
            editable.add(sid)
        except Exception:
            continue
    return editable


def _accessible_project_options(db_session, current_user) -> list[dict]:
    """Projects (sites) on which the user has Diligence ``edit``. Platform-bypass sees all
    non-archived sites.

    Read-only and authz-scoped to the Diligence ``edit`` set (NOT mere site visibility) so the
    project dropdown never lists a project the user could not open/edit in the Data Room. The
    underlying upload/parse endpoints remain the authoritative per-site guard at execute time.
    """
    from app.models.site import Site

    query = db_session.query(Site.id, Site.name).filter(Site.is_archived.is_(False))
    site_ids = _diligence_editable_site_ids(db_session, current_user)
    if site_ids is not None:
        if not site_ids:
            return []
        query = query.filter(Site.id.in_(list(site_ids)))
    rows = query.order_by(Site.name).all()
    return [{"label": name or f"Project {sid}", "value": str(sid)} for sid, name in rows]


def _project_documents_options(db_session, current_user, context: Optional[dict]) -> list[dict]:
    """Document slots for the project selected in context (``site_id``), Diligence-edit scoped."""
    site_id = _ctx_int(context, "site_id")
    if site_id is None:
        return []
    site_ids = _diligence_editable_site_ids(db_session, current_user)
    if site_ids is not None and site_id not in site_ids:
        return []
    from app.crud.document import DocumentCRUD

    docs = DocumentCRUD(db_session).get_site_documents_ordered_by_name(site_id)
    out: list[dict] = []
    for doc in docs:
        label = getattr(doc, "custom_name", None)
        if not label:
            name = getattr(doc, "name", None)
            label = name.value if getattr(name, "value", None) else f"Document {doc.id}"
        out.append({"label": label, "value": str(doc.id)})
    return out


def _document_files_options(db_session, current_user, context: Optional[dict]) -> list[dict]:
    """Uploaded files for the document selected in context (``document_id``), Diligence-edit scoped."""
    document_id = _ctx_int(context, "document_id")
    if document_id is None:
        return []
    from app.crud.document import DocumentCRUD
    from app.crud.file import FileCRUD

    doc = DocumentCRUD(db_session).get_by_id(document_id)
    if doc is None:
        return []
    site_ids = _diligence_editable_site_ids(db_session, current_user)
    if site_ids is not None and getattr(doc, "site_id", None) not in site_ids:
        return []
    files = FileCRUD(db_session).get_document_files(document_id)
    out: list[dict] = []
    for f in files:
        label = getattr(f, "filename", None) or f"File {f.id}"
        version = getattr(f, "version_number", None)
        if version:
            label = f"{label} (v{version})"
        out.append({"label": label, "value": str(f.id)})
    return out


def _membership_company_options(db_session, current_user) -> list[dict]:
    """Companies the user may add a member to: platform-bypass sees all active companies; a
    normal user sees only companies where they are a company admin. Read-only; the existing
    add-member endpoint remains the authoritative per-company guard at execute time.
    """
    from app.models.company import Company

    if getattr(current_user, "has_platform_bypass", False):
        rows = (
            db_session.query(Company.id, Company.name)
            .filter(Company.is_archived.is_(False))
            .order_by(Company.name)
            .all()
        )
        return [{"label": name, "value": str(cid)} for cid, name in rows]

    try:
        company_ids = current_user.get_limited_companies_ids() or []
    except Exception:
        company_ids = []
    if not company_ids:
        return []

    from app.crud.user_company_access import UserCompanyAccessCRUD

    access_crud = UserCompanyAccessCRUD(db_session)
    names = {
        c.id: c.name
        for c in db_session.query(Company)
        .filter(Company.id.in_(company_ids), Company.is_archived.is_(False))
        .all()
    }
    out: list[dict] = []
    for cid in company_ids:
        name = names.get(cid)
        if name is None:
            continue
        try:
            if access_crud.is_company_admin(current_user.id, cid):
                out.append({"label": name, "value": str(cid)})
        except Exception:
            continue
    out.sort(key=lambda o: o["label"].lower())
    return out


def _membership_role_options() -> list[dict]:
    """The company roles a user can be granted (static enum)."""
    return [{"label": r.value, "value": r.value} for r in CompanyRoleEnum]


def resolve_options(
    options_source: Optional[str], db_session=None, current_user=None, context: Optional[dict] = None
) -> Optional[list[dict]]:
    """Resolve a select field's ``options_source`` to concrete {label, value} options.

    Static sources ignore ``db_session``/``current_user``/``context``; dynamic sources require
    ``db_session`` + ``current_user`` and return [] when they are unavailable. Cascading
    sources (``project_documents``, ``document_files``) additionally read ``context`` — the
    run's already-collected inputs — to scope to the chosen project/document. Every dynamic
    source is read-only and authz-scoped; the existing endpoints remain the authoritative guards.
    """
    if options_source is None:
        return None
    if options_source == "company_types":
        return [{"label": ct.value, "value": ct.value} for ct in CompanyTypes]
    if options_source == "us_states":
        return [{"label": st.value, "value": st.value} for st in State]
    if options_source == "us_timezones":
        return [{"label": label, "value": value} for value, label in _US_TIMEZONES]
    if options_source == "membership_roles":
        return _membership_role_options()
    if db_session is None or current_user is None:
        return []
    if options_source == "companies":
        return _editable_company_options(db_session, current_user)
    if options_source == "accessible_projects":
        return _accessible_project_options(db_session, current_user)
    if options_source == "project_documents":
        return _project_documents_options(db_session, current_user, context)
    if options_source == "document_files":
        return _document_files_options(db_session, current_user, context)
    if options_source == "membership_companies":
        return _membership_company_options(db_session, current_user)
    return []


# --- Thin target-selector schemas for the new workflows -------------------------------
#
# These are NOT parallel mutation paths. Add Company/Add Site validate the merged inputs
# directly against their full domain schema (CreateCompanySchema/CreateSiteSchema). The Invite
# User / Document Upload / Parse Document workflows instead COLLECT a small set of targets
# (who/where/which file); the executor maps those targets onto the EXISTING domain schemas
# (CreateUserSchema + UserCompanyAccessCreate) or endpoint args, which perform the authoritative
# validation. The schemas below validate only the collected targets (presence + basic shape),
# coercing the str-valued select inputs to their proper types.


class InviteUserInputs(BaseModel):
    """Collected targets for Invite User. Mapped to CreateUserSchema + UserCompanyAccessCreate
    by the executor (which performs the authoritative domain validation)."""

    email: EmailStr
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    company_id: int
    role: CompanyRoleEnum = CompanyRoleEnum.contributor


class UploadTargetInputs(BaseModel):
    """Collected destination for Document Upload (the file bytes travel separately, multipart)."""

    site_id: int
    document_id: int


class ParseTargetInputs(BaseModel):
    """Collected target file for Parse Document (project -> document -> file cascade)."""

    site_id: int
    document_id: int
    file_id: int


# Per-(workflow, step) server validator for a COLLECT step's inputs. Reused to validate a
# saved step (best-effort, non-blocking) and is the SAME schema the real endpoint enforces.
STEP_INPUT_SCHEMAS: dict[tuple[str, str], type[BaseModel]] = {
    ("add_company", "company_details"): CreateCompanySchema,
    ("add_site", "project_details"): CreateSiteSchema,
    ("invite_user", "invitee_details"): InviteUserInputs,
    ("document_upload", "select_target"): UploadTargetInputs,
    ("parse_document", "select_file"): ParseTargetInputs,
}

# Per-workflow payload schema used to validate the merged inputs of a write step before it is
# dispatched to the existing endpoint. For Add Company/Add Site this is the EXISTING domain
# schema; for the new workflows it is the thin target-selector schema above (the executor maps
# the validated targets onto the existing domain schemas/endpoints).
WORKFLOW_PAYLOAD_SCHEMAS: dict[str, type[BaseModel]] = {
    "add_company": CreateCompanySchema,
    "add_site": CreateSiteSchema,
    "invite_user": InviteUserInputs,
    "document_upload": UploadTargetInputs,
    "parse_document": ParseTargetInputs,
}


def get_step_input_schema(workflow_id: str, step_id: str) -> Optional[type[BaseModel]]:
    return STEP_INPUT_SCHEMAS.get((workflow_id, step_id))


def get_payload_schema(workflow_id: str) -> Optional[type[BaseModel]]:
    return WORKFLOW_PAYLOAD_SCHEMAS.get(workflow_id)
