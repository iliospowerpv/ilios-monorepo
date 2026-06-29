"""Read-only tool catalog for the AI Assistant.

Every tool here is a thin wrapper over an EXISTING authorized read-only service. Each handler runs
AS the caller (``current_user`` is threaded straight through), so authorization is enforced by the
underlying service exactly as it is for the Workflow Dashboard — the assistant never widens scope and
never bypasses permissions. Handlers return plain JSON-serializable dicts (``model_dump(mode="json")``)
so the result can be fed back to the model. NONE of these perform writes, commits, or governed actions.

``dispatch_tool`` is the single choke point: it runs the guardrail check before any handler executes.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.services.assistant import guardrails
from app.services.assistant.faq import search_faq
from app.services.workflows.engine import (
    compute_metrics,
    list_sequences,
    list_user_runs,
    list_workflow_definitions,
)
from app.services.workflows.onboarding_progress_service import build_onboarding_progress
from app.services.workflows.orchestration_context_service import build_orchestration_context
from app.services.workflows.readiness_summary_service import build_readiness_summary
from app.services.workflows.recommendations_service import build_recommendations

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


def _t_answer_help_faq(db: Session, user, args: dict) -> dict:
    return {"results": search_faq(str(args.get("query") or ""), limit=_clamp(args.get("limit"), 4))}


TOOL_HANDLERS: dict[str, Callable[[Session, Any, dict], dict]] = {
    "list_workflows": _t_list_workflows,
    "list_sequences": _t_list_sequences,
    "list_my_runs": _t_list_my_runs,
    "get_recommendations": _t_get_recommendations,
    "get_onboarding_progress": _t_get_onboarding_progress,
    "get_onboarding_readiness": _t_get_onboarding_readiness,
    "get_orchestration_context": _t_get_orchestration_context,
    "get_workflow_metrics": _t_get_workflow_metrics,
    "answer_help_faq": _t_answer_help_faq,
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


def _spec(name: str, description: str, properties: dict | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "additionalProperties": False,
            },
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
        "answer_help_faq",
        "Look up curated product help / FAQ entries (what iliOS is, Project vs Site, how to onboard, "
        "what workflows are, what the assistant can/can't do). Returns grounding text to answer "
        "general 'how do I' / 'what is' questions.",
        {"query": {"type": "string", "description": "The user's help/FAQ question."}, "limit": _LIMIT_PROP},
    ),
]


def dispatch_tool(db_session: Session, current_user, name: str, args: dict) -> dict:
    """Guardrail-check, then run a read-only tool. Raises ``AssistantGuardrailError`` if blocked.

    Authorization for the data itself is enforced inside each wrapped service via ``current_user``.
    """
    guardrails.assert_tool_allowed(name, ALLOWED_TOOLS)
    handler = TOOL_HANDLERS[name]
    return handler(db_session, current_user, args or {})
