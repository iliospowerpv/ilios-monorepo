"""Read-only tool catalog for the AI Assistant.

Every tool here is a thin wrapper over an EXISTING read-only service. Handlers run AS the caller
(``current_user`` is threaded straight through) and never widen scope or bypass permissions.
Authorization is enforced one of two equivalent ways depending on the wrapped service:

* Some services self-authorize from ``current_user`` (the workspace/onboarding tools) — exactly as
  they do for the Workflow Dashboard.
* The per-site summary tools wrap services that authorize at the ROUTER layer (e.g.
  ``Depends(get_authorized_site)``), NOT internally. For those the tool layer reproduces the same
  router-equivalent guards (site visibility, ``Diligence:view``) BEFORE calling the service, and
  returns an honest "unavailable" envelope without ever invoking the service on denial.

Handlers return plain JSON-serializable dicts (``model_dump(mode="json")``) so the result can be fed
back to the model. NONE of these perform writes, commits, or governed actions.

``dispatch_tool`` is the single choke point: it runs the guardrail check before any handler executes.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.data_room_template import DataRoomTemplateCRUD
from app.crud.document import DocumentCRUD
from app.crud.document_section import DocumentSectionCRUD
from app.helpers.due_diligence.expected_documents import get_expected_documents_for_section
from app.services.assistant import guardrails
from app.services.assistant.action_cards import build_action_card
from app.services.assistant.faq import search_faq
from app.services.due_diligence.data_room_guidance_service import DataRoomGuidanceService
from app.services.due_diligence.reconciliation_service import build_site_reconciliation
from app.services.project_facts_service import ProjectFactsService
from app.services.telemetry.device_eligibility_diagnostics_service import (
    compute_site_eligibility_diagnostics,
)
from app.services.telemetry.device_inventory_reconciliation_service import (
    build_site_inventory_reconciliation,
)
from app.services.telemetry.expected_service import compute_site_expected_period_effective
from app.services.telemetry.health_service import compute_site_telemetry_health
from app.services.weather.weather_readiness_service import compute_weather_readiness
from app.services.workflows.engine import (
    compute_metrics,
    get_run,
    list_sequences,
    list_user_runs,
    list_workflow_definitions,
)
from app.services.workflows.onboarding_common import (
    can_view_diligence,
    resolve_candidate_sites,
)
from app.services.workflows.onboarding_progress_service import build_onboarding_progress
from app.services.workflows.orchestration_context_service import build_orchestration_context
from app.services.workflows.readiness_summary_service import build_readiness_summary
from app.services.workflows.recommendations_service import build_recommendations
from app.static.default_site_documents_enum import DocumentSections

logger = logging.getLogger(__name__)

# Defensive cap so a model can never request an unbounded fan-out through the assistant.
_MAX_LIMIT = 25


def _clamp(value: Any, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, _MAX_LIMIT))


def _opt_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


# --- Phase 1: per-domain summary helpers (authz + time window) --------------------------------
#
# The per-site summary tools below wrap EXISTING read services that authorize at the ROUTER layer
# (via ``Depends(get_authorized_site)`` etc.), NOT internally. So the assistant reproduces the same
# guards here BEFORE calling them: the requested ``site_id`` is intersected with the caller's
# visible set (fail-closed), and diligence-derived tools additionally require the same
# ``Diligence:view`` the reconciliation endpoint enforces. A denied/unknown id returns an honest
# "unavailable" envelope and the wrapped service is NEVER called, so no scope is ever widened.

_BUCKET_SIZES = ("15m", "30m", "1h", "1d")
_DEFAULT_BUCKET = "1h"
_DEFAULT_WINDOW_DAYS = 1
_MAX_WINDOW_DAYS = 31


def _resolve_authorized_site(db: Session, user, args: dict):
    """Return the caller-visible ``Site`` for ``args['site_id']`` or ``None`` (fail-closed).

    Uses the same visibility intersection the onboarding rollups use, so an id the caller cannot
    see resolves to ``None`` rather than disclosing anything.
    """
    site_id = _opt_int(args.get("site_id"))
    if site_id is None:
        return None
    sites = resolve_candidate_sites(db, user, site_id=site_id, limit=1)
    return sites[0] if sites else None


def _unavailable(reason: str, site_id: int | None) -> dict:
    """Honest 'no data disclosed' envelope returned in place of calling a wrapped service."""
    return {"available": False, "reason": reason, "site_id": site_id}


def _resolve_window(args: dict) -> tuple[datetime, datetime, str, int]:
    """Resolve a clamped, naive-UTC ``(start, end, bucket_size, days)`` from optional args.

    Picking a default window/bucket is parameterization (plumbing), not calculation — every value
    is computed by the wrapped service. The resolved window is disclosed back in the tool result so
    the model (and user) always know the exact scope summarized.
    """
    try:
        days = int(args.get("days"))
    except (TypeError, ValueError):
        days = _DEFAULT_WINDOW_DAYS
    days = max(1, min(days, _MAX_WINDOW_DAYS))
    bucket = args.get("bucket_size")
    if bucket not in _BUCKET_SIZES:
        bucket = _DEFAULT_BUCKET
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    return start, end, bucket, days


def _window_disclosure(start: datetime, end: datetime, bucket: str, days: int) -> dict:
    return {
        "days": days,
        "bucket_size": bucket,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }


def _latest_document_version(document) -> int:
    """Highest non-deleted file version_number for a Document (0 when none). Pure read."""
    versions = [f.version_number or 0 for f in document.files if not f.deleted]
    return max(versions) if versions else 0


def _count_template_structure(structure: dict) -> tuple[int, int]:
    """Count (sections, documents) in a Data Room template structure snapshot. Pure read."""
    sections = structure.get("sections", []) if isinstance(structure, dict) else []
    document_count = 0
    for section in sections:
        document_count += len(section.get("documents", []) or [])
        for sub in section.get("subsections", []) or []:
            document_count += len(sub.get("documents", []) or [])
    return len(sections), document_count


# --- Handlers (db_session, current_user, args) -> JSON-serializable dict ----------------------


def _t_list_workflows(db: Session, user, args: dict) -> dict:
    return list_workflow_definitions(db, user).model_dump(mode="json")


def _t_list_sequences(db: Session, user, args: dict) -> dict:
    return list_sequences(db, user).model_dump(mode="json")


def _t_list_my_runs(db: Session, user, args: dict) -> dict:
    return list_user_runs(db, user, limit=_clamp(args.get("limit"), 20)).model_dump(mode="json")


def _t_get_recommendations(db: Session, user, args: dict) -> dict:
    return build_recommendations(db, user, limit=_clamp(args.get("limit"), 10)).model_dump(
        mode="json"
    )


def _t_get_onboarding_progress(db: Session, user, args: dict) -> dict:
    return build_onboarding_progress(
        db,
        user,
        site_id=_opt_int(args.get("site_id")),
        company_id=_opt_int(args.get("company_id")),
        limit=_clamp(args.get("limit"), 10),
    ).model_dump(mode="json")


def _t_get_onboarding_readiness(db: Session, user, args: dict) -> dict:
    return build_readiness_summary(
        db,
        user,
        site_id=_opt_int(args.get("site_id")),
        company_id=_opt_int(args.get("company_id")),
        limit=_clamp(args.get("limit"), 10),
    ).model_dump(mode="json")


def _t_get_orchestration_context(db: Session, user, args: dict) -> dict:
    return build_orchestration_context(db, user, limit=_clamp(args.get("limit"), 10)).model_dump(
        mode="json"
    )


def _t_get_workflow_metrics(db: Session, user, args: dict) -> dict:
    return compute_metrics(db, user, scope="me").model_dump(mode="json")


def _t_get_workflow_run(db: Session, user, args: dict) -> dict:
    """Wrap ``engine.get_run`` — owner-scoped detail for ONE of the caller's OWN workflow runs.

    This is the Workflow Companion's grounding read. ``get_run`` self-authorizes via
    ``_get_run_owned`` (``WorkflowRunCRUD.get_for_user``), so a run the caller does not own raises
    404 and we return an honest 'unavailable' envelope without disclosing anything. The result is
    the serialized run state (status, current_step, each step's persisted inputs + validation_errors)
    plus the workflow definition (step/field schemas, confirmation text, prerequisites,
    blocked_reason) — everything needed to EXPLAIN the wizard. STRICTLY read-only: it never starts,
    saves, previews, or executes a step.
    """
    run_id = _opt_int(args.get("run_id"))
    if run_id is None:
        return {"available": False, "reason": "missing_run_id", "run_id": None}
    try:
        return get_run(db, user, run_id).model_dump(mode="json")
    except HTTPException:
        # Owner-scoped fetch denied / not found (cross-user or unknown run) — disclose nothing.
        return {"available": False, "reason": "not_authorized_or_not_found", "run_id": run_id}


def _t_answer_help_faq(db: Session, user, args: dict) -> dict:
    return {"results": search_faq(str(args.get("query") or ""), limit=_clamp(args.get("limit"), 4))}


def _t_propose_action_card(db: Session, user, args: dict) -> dict:
    """Validate (read-only) that the caller MAY take a workflow/sequence/resume action and, if so,
    return an inert deep-link card the USER can click. Never starts/executes anything — producing a
    link is not a governed action, so this is genuinely read-only. Denied (no card) when not allowed.
    """
    return build_action_card(
        db,
        user,
        kind=str(args.get("kind") or ""),
        workflow_id=(args.get("workflow_id") or None),
        sequence_id=(args.get("sequence_id") or None),
        run_id=_opt_int(args.get("run_id")),
        site_id=_opt_int(args.get("site_id")),
        company_id=_opt_int(args.get("company_id")),
        reason=(args.get("reason") or None),
        target_view=(args.get("target_view") or None),
        prompt=(args.get("prompt") or None),
        current_route=(args.get("current_route") or None),
    )


# --- Phase 1: per-domain summary tools (each wraps EXACTLY ONE native read service) ------------


def _t_get_site_telemetry_health(db: Session, user, args: dict) -> dict:
    """Wrap ``compute_site_telemetry_health`` — a project's telemetry connection/freshness state."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    return compute_site_telemetry_health(db, site).model_dump(mode="json")


def _t_get_site_diligence_reconciliation(db: Session, user, args: dict) -> dict:
    """Wrap ``build_site_reconciliation`` — the read-only DD reconciliation ladder for a project."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    if not can_view_diligence(db, user, site):
        return _unavailable("diligence_view_not_permitted", site.id)
    return build_site_reconciliation(db, site).model_dump(mode="json")


def _t_get_site_weather_readiness(db: Session, user, args: dict) -> dict:
    """Wrap ``compute_weather_readiness`` — historical-weather replay readiness for a window."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    start, end, bucket, days = _resolve_window(args)
    result = compute_weather_readiness(
        db, site_id=site.id, start=start, end=end, bucket_size=bucket
    ).model_dump(mode="json")
    result["window"] = _window_disclosure(start, end, bucket, days)
    return result


def _t_get_site_active_facts(db: Session, user, args: dict) -> dict:
    """Wrap ``ProjectFactsService.get_active_facts`` — a project's active (accepted) DD facts."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    if not can_view_diligence(db, user, site):
        return _unavailable("diligence_view_not_permitted", site.id)
    return {"site_id": site.id, "facts": ProjectFactsService(db).get_active_facts(site.id)}


def _t_get_site_expected_summary(db: Session, user, args: dict) -> dict:
    """Wrap ``compute_site_expected_period_effective`` — weather-adjusted expected vs actual."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    start, end, bucket, days = _resolve_window(args)
    result = compute_site_expected_period_effective(
        db, site=site, start=start, end=end, bucket_size=bucket
    ).model_dump(mode="json")
    result["window"] = _window_disclosure(start, end, bucket, days)
    return result


def _t_get_site_inventory_reconciliation(db: Session, user, args: dict) -> dict:
    """Wrap ``build_site_inventory_reconciliation`` — discovered vs mapped device inventory."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    return build_site_inventory_reconciliation(db, site).model_dump(mode="json")


def _t_get_site_device_eligibility(db: Session, user, args: dict) -> dict:
    """Wrap ``compute_site_eligibility_diagnostics`` — per-device telemetry eligibility diagnostics."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    return compute_site_eligibility_diagnostics(db, site=site).model_dump(mode="json")


# --- Phase 2: Data Room awareness tools (Task #93) -------------------------------------------
#
# These wrap the Task #90–92 read services so the assistant can EXPLAIN a project's Data Room —
# expected vs missing documents, per-stage completeness, document identity & existing versions, and
# the reusable structure templates available for the company. Each is strictly read-only and, like
# the diligence reconciliation tool above, mirrors the router guard (site visibility + Diligence
# view) BEFORE touching the wrapped service. They never upload, promote, archive, delete, or move
# anything — at most the assistant proposes an inert ``open`` deep-link into the Data Room view.


def _t_get_site_data_room_guidance(db: Session, user, args: dict) -> dict:
    """Wrap ``DataRoomGuidanceService.build_guidance`` — per-stage Data Room completeness.

    Returns, for each stage that defines expectations: expected/present/missing counts, the list of
    missing documents, needs-update / optional / archived counts, total version count, and the
    stage's promotion rollup. This grounds 'what's still missing?', 'why is this stage incomplete?',
    and 'what belongs in [stage]?'. Requires Diligence view (mirrors the guidance endpoint)."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    if not can_view_diligence(db, user, site):
        return _unavailable("diligence_view_not_permitted", site.id)
    result = DataRoomGuidanceService(db).build_guidance(site.id)
    result["site_id"] = site.id
    return result


def _t_get_site_expected_documents(db: Session, user, args: dict) -> dict:
    """Wrap the static Expected Documents catalog (``get_expected_documents_for_section``).

    Mirrors the ``/expected-documents`` endpoint: the per-stage list of documents the catalog
    expects (kind, name, description, required, position), correlated with the site's section ids.
    Declarative only — it never materializes a Document/File row. Answers 'what belongs in [stage]?'
    with full descriptions. Requires Diligence view."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    if not can_view_diligence(db, user, site):
        return _unavailable("diligence_view_not_permitted", site.id)
    section_id_by_key = {
        section.name.name: section.id
        for section in DocumentSectionCRUD(db).get_site_sections(site.id)
    }
    items = []
    for section in DocumentSections:
        expected = get_expected_documents_for_section(section)
        if not expected:
            continue
        items.append(
            {
                "section_id": section_id_by_key.get(section.name),
                "section_key": section.name,
                "section_name": section.value,
                "expected_documents": expected,
            }
        )
    return {"site_id": site.id, "items": items}


def _t_get_site_data_room_documents(db: Session, user, args: dict) -> dict:
    """List the site's live Document IDENTITIES with their existing version counts.

    Wraps ``DocumentCRUD.get_site_documents_ordered_by_name``. For each document it returns the
    resolved identity name, stable kind, aliases, section, archived flag, how many file versions
    exist, and the latest version number. This grounds 'should this be a NEW document or a new
    VERSION of an existing one?' (an identity already exists -> upload a new version to it) and
    document-identity questions. Requires Diligence view. Read-only — never uploads/mutates."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    if not can_view_diligence(db, user, site):
        return _unavailable("diligence_view_not_permitted", site.id)
    documents = DocumentCRUD(db).get_site_documents_ordered_by_name(site.id)
    items = [
        {
            "document_id": document.id,
            "display_name": document.identity_name,
            "kind": document.identity_kind,
            "aliases": document.identity_aliases,
            "section_id": document.section_id,
            "section_name": (
                document.section.name.value
                if document.section and document.section.name
                else None
            ),
            "is_archived": document.is_archived,
            "version_count": document.files_count,
            "latest_version": _latest_document_version(document),
        }
        for document in documents
    ]
    return {"site_id": site.id, "items": items}


def _t_get_site_data_room_templates(db: Session, user, args: dict) -> dict:
    """List the reusable Data Room STRUCTURE templates available for the project's company.

    Wraps ``DataRoomTemplateCRUD.get_by_company`` (mirroring the template list endpoint). Templates
    are company-scoped structure-only snapshots (stages + expected documents); applying one scaffolds
    a NEW Data Room at site creation — it never reconciles an existing one. Returns id/name/
    description/archived plus section & document counts. Requires Diligence view. Read-only."""
    site = _resolve_authorized_site(db, user, args)
    if site is None:
        return _unavailable("not_authorized_or_not_found", _opt_int(args.get("site_id")))
    if not can_view_diligence(db, user, site):
        return _unavailable("diligence_view_not_permitted", site.id)
    templates = DataRoomTemplateCRUD(db).get_by_company(site.company_id, include_archived=False)
    items = []
    for template in templates:
        section_count, document_count = _count_template_structure(template.structure or {})
        items.append(
            {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "is_archived": template.is_archived,
                "section_count": section_count,
                "document_count": document_count,
            }
        )
    return {"site_id": site.id, "company_id": site.company_id, "items": items}


TOOL_HANDLERS: dict[str, Callable[[Session, Any, dict], dict]] = {
    "list_workflows": _t_list_workflows,
    "list_sequences": _t_list_sequences,
    "list_my_runs": _t_list_my_runs,
    "get_recommendations": _t_get_recommendations,
    "get_onboarding_progress": _t_get_onboarding_progress,
    "get_onboarding_readiness": _t_get_onboarding_readiness,
    "get_orchestration_context": _t_get_orchestration_context,
    "get_workflow_metrics": _t_get_workflow_metrics,
    "get_workflow_run": _t_get_workflow_run,
    "answer_help_faq": _t_answer_help_faq,
    "propose_action_card": _t_propose_action_card,
    "get_site_telemetry_health": _t_get_site_telemetry_health,
    "get_site_diligence_reconciliation": _t_get_site_diligence_reconciliation,
    "get_site_weather_readiness": _t_get_site_weather_readiness,
    "get_site_active_facts": _t_get_site_active_facts,
    "get_site_expected_summary": _t_get_site_expected_summary,
    "get_site_inventory_reconciliation": _t_get_site_inventory_reconciliation,
    "get_site_device_eligibility": _t_get_site_device_eligibility,
    "get_site_data_room_guidance": _t_get_site_data_room_guidance,
    "get_site_expected_documents": _t_get_site_expected_documents,
    "get_site_data_room_documents": _t_get_site_data_room_documents,
    "get_site_data_room_templates": _t_get_site_data_room_templates,
}

# Single source of truth for the allowlist (guardrails screens names against this set + keywords).
ALLOWED_TOOLS: frozenset[str] = frozenset(TOOL_HANDLERS)

_LIMIT_PROP = {
    "type": "integer",
    "description": f"Max items to return (1-{_MAX_LIMIT}).",
    "minimum": 1,
    "maximum": _MAX_LIMIT,
}
_SITE_PROP = {"type": "integer", "description": "Optional Site/Project id to scope to."}
_COMPANY_PROP = {"type": "integer", "description": "Optional Company id to scope to."}
_REQ_SITE_PROP = {
    "type": "integer",
    "description": "Site/Project id to summarize (required). Use the site_id from the current "
    "page context when the user means 'this project'.",
}
_DAYS_PROP = {
    "type": "integer",
    "description": f"Look-back window in days (1-{_MAX_WINDOW_DAYS}); default {_DEFAULT_WINDOW_DAYS}.",
    "minimum": 1,
    "maximum": _MAX_WINDOW_DAYS,
}
_BUCKET_PROP = {
    "type": "string",
    "enum": list(_BUCKET_SIZES),
    "description": f"Time bucket size; default {_DEFAULT_BUCKET}.",
}


def _spec(
    name: str,
    description: str,
    properties: dict | None = None,
    required: list[str] | None = None,
) -> dict:
    parameters: dict = {
        "type": "object",
        "properties": properties or {},
        "additionalProperties": False,
    }
    if required:
        parameters["required"] = list(required)
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


# OpenAI function-calling schemas advertised to the model. Read-only verbs only.
TOOL_SPECS: list[dict] = [
    _spec(
        "list_workflows",
        "List the guided workflows (wizards) the current user is allowed to run, with title and "
        "description. Read-only; does NOT start anything.",
    ),
    _spec(
        "list_sequences",
        "List the multi-step guided sequences (e.g. onboarding, portfolio_setup, site_diligence) "
        "available to the current user. Read-only.",
    ),
    _spec(
        "list_my_runs",
        "List the current user's own workflow runs and their status (to explain what is in "
        "progress). Read-only; owner-scoped.",
        {"limit": _LIMIT_PROP},
    ),
    _spec(
        "get_recommendations",
        "Get the deterministic, read-only 'recommended next actions' for the current user, each "
        "with a reason and the route to take the action manually. Advice only — never executed.",
        {"limit": _LIMIT_PROP},
    ),
    _spec(
        "get_onboarding_progress",
        "Get per-project onboarding stage checklists (which setup stages are done vs pending) for "
        "the projects the user can see. Read-only.",
        {"site_id": _SITE_PROP, "company_id": _COMPANY_PROP, "limit": _LIMIT_PROP},
    ),
    _spec(
        "get_onboarding_readiness",
        "Get per-project readiness across telemetry health, due-diligence reconciliation, device "
        "eligibility, and expected baseline. Honest 'unavailable' when a section can't be "
        "evaluated. Read-only.",
        {"site_id": _SITE_PROP, "company_id": _COMPANY_PROP, "limit": _LIMIT_PROP},
    ),
    _spec(
        "get_orchestration_context",
        "Get the full read-only orchestration envelope (available workflows, sequences, runs "
        "summary, metrics, progress, readiness, recommendations, and the prohibited-actions "
        "contract) in one call. Read-only advice envelope.",
        {"limit": _LIMIT_PROP},
    ),
    _spec(
        "get_workflow_metrics",
        "Get summary counts/metrics about the current user's workflow activity. Read-only.",
    ),
    _spec(
        "get_workflow_run",
        "Get the full read-only detail of ONE of the CURRENT USER'S OWN workflow runs (the guided "
        "wizard they are in). Returns the run status and current step, every step's saved inputs and "
        "any validation errors the user already hit, plus the workflow definition: each step's fields "
        "(name/label/type/required/help/placeholder), the confirmation text shown before the final "
        "action, the governed flag, prerequisites, and blocked_reason. Use this in Workflow Companion "
        "Mode to explain the current step, what a field means, why an entry failed validation, what "
        "the confirm/execute step will do, how to resume, or why the workflow is blocked. STRICTLY "
        "read-only — it does NOT start, save, preview, or execute any step; the user performs every "
        "action themselves in the wizard. Provide run_id (use the run_id from the UI context when the "
        "user means 'this wizard'). A run the user does not own returns available=false.",
        {"run_id": {"type": "integer", "description": "The caller's OWN workflow run id to describe."}},
        required=["run_id"],
    ),
    _spec(
        "answer_help_faq",
        "Look up curated product help / FAQ entries (what iliOS is, Project vs Site, how to onboard, "
        "what workflows are, what the assistant can/can't do). Returns grounding text to answer "
        "general 'how do I' / 'what is' questions.",
        {"query": {"type": "string", "description": "The user's help/FAQ question."}, "limit": _LIMIT_PROP},
    ),
    _spec(
        "propose_action_card",
        "Propose ONE inert deep-link 'action card' the USER can click to take the next step "
        "themselves in the existing UI. This is READ-ONLY: it only validates the user is allowed to "
        "reach/start/resume the target and returns a link — it NEVER starts, advances, or executes "
        "anything. Use this when you recommend a concrete next step so the user gets a clickable "
        "shortcut. If the user lacks permission, no card is returned (say so honestly). "
        "kind='workflow' needs workflow_id (optionally site_id/company_id to scope); kind='sequence' "
        "needs sequence_id; kind='resume' needs run_id (one of the user's own open runs); "
        "kind='open' deep-links an EXISTING read view chosen by target_view (project_overview / "
        "data_room / reconciliation / site_finance need site_id; company_finance needs company_id) "
        "— the route is derived server-side, you NEVER supply a raw URL; kind='explain' re-asks the "
        "read-only chat a canned question (supply prompt). Always make clear the user must click it.",
        {
            "kind": {
                "type": "string",
                "enum": ["workflow", "sequence", "resume", "open", "explain"],
                "description": "What the card links to.",
            },
            "workflow_id": {"type": "string", "description": "Required when kind='workflow'."},
            "sequence_id": {"type": "string", "description": "Required when kind='sequence'."},
            "run_id": {"type": "integer", "description": "Required when kind='resume' (caller's own run)."},
            "target_view": {
                "type": "string",
                "enum": [
                    "project_overview",
                    "data_room",
                    "reconciliation",
                    "site_finance",
                    "company_finance",
                ],
                "description": "Required when kind='open': which EXISTING read view to deep-link to "
                "(route derived server-side from this + scope; never a raw URL).",
            },
            "prompt": {
                "type": "string",
                "description": "Required when kind='explain': the canned read-only question to "
                "re-submit into the chat.",
            },
            "current_route": {
                "type": "string",
                "description": "Optional for kind='explain': the page being explained (for context).",
            },
            "site_id": _SITE_PROP,
            "company_id": _COMPANY_PROP,
            "reason": {
                "type": "string",
                "description": "Short, honest one-line reason this step helps (shown on the card).",
            },
        },
    ),
    _spec(
        "get_site_telemetry_health",
        "Summarize ONE project's telemetry health: connection/mapping state, data freshness/delay, "
        "expected interval, and mapped-device count. Use to answer 'is data flowing for this "
        "project?'. Read-only; needs site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_diligence_reconciliation",
        "Summarize ONE project's due-diligence reconciliation ladder (how AI-extracted facts "
        "reconcile against accepted baselines/overrides). Requires Diligence view permission — "
        "returns an honest 'not permitted' if the caller lacks it. Read-only; needs site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_weather_readiness",
        "Summarize ONE project's historical-weather replay readiness over a recent window "
        "(usable POA / cell-temperature coverage, gaps, unknown-semantics, governing profile). "
        "Honest gaps, never fabricated. Read-only; needs site_id.",
        {"site_id": _REQ_SITE_PROP, "days": _DAYS_PROP, "bucket_size": _BUCKET_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_active_facts",
        "List ONE project's ACTIVE (accepted) due-diligence facts/assumptions (the canonical "
        "values currently in effect). Requires Diligence view permission — honest 'not permitted' "
        "otherwise. Read-only; needs site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_expected_summary",
        "Summarize ONE project's weather-adjusted expected-vs-actual energy over a recent window "
        "(uses the baseline active in each period; expected is honest N/A — never 0 — when inputs "
        "or a valid baseline are missing). Read-only; needs site_id.",
        {"site_id": _REQ_SITE_PROP, "days": _DAYS_PROP, "bucket_size": _BUCKET_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_inventory_reconciliation",
        "Summarize ONE project's device inventory reconciliation: provider-discovered devices vs "
        "mapped devices, gaps, and discovery staleness. Read-only; needs site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_device_eligibility",
        "Summarize ONE project's per-device telemetry eligibility diagnostics (which devices are "
        "mappable / drive expected, and the blocking reasons for those that don't). Read-only; "
        "needs site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_data_room_guidance",
        "Summarize ONE project's Data Room completeness per stage: expected/present/missing counts, "
        "the list of MISSING documents, needs-update/optional/archived counts, version totals, and "
        "promotion status. Use to answer 'what documents are still missing?' or 'why is this stage "
        "incomplete?'. Requires Diligence view — honest 'not permitted' otherwise. Read-only; needs "
        "site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_expected_documents",
        "List the EXPECTED documents catalog for ONE project, grouped by stage (kind, name, "
        "description, required flag), correlated with the project's section ids. Use to answer 'what "
        "belongs in [stage]?'. Declarative catalog — never creates rows. Requires Diligence view. "
        "Read-only; needs site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_data_room_documents",
        "List ONE project's existing Data Room document IDENTITIES: resolved name, kind, aliases, "
        "section, archived flag, how many file versions exist, and the latest version number. Use to "
        "answer 'should this be a new document or a new VERSION of an existing one?'. Requires "
        "Diligence view. Read-only; needs site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
    _spec(
        "get_site_data_room_templates",
        "List the reusable Data Room STRUCTURE templates available for the project's company "
        "(id, name, description, section & document counts). Templates scaffold a NEW Data Room at "
        "project creation; they never reconcile an existing one. Requires Diligence view. Read-only; "
        "needs site_id.",
        {"site_id": _REQ_SITE_PROP},
        required=["site_id"],
    ),
]


def dispatch_tool(db_session: Session, current_user, name: str, args: dict) -> dict:
    """Guardrail-check, then run a read-only tool. Raises ``AssistantGuardrailError`` if blocked.

    Authorization for the underlying data is enforced per the module docstring: workspace/onboarding
    tools self-authorize from ``current_user``, while the per-site summary tools apply the same
    router-equivalent guards in the handler before calling the wrapped service.
    """
    guardrails.assert_tool_allowed(name, ALLOWED_TOOLS)
    handler = TOOL_HANDLERS[name]
    return handler(db_session, current_user, args or {})
