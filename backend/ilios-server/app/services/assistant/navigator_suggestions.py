"""Deterministic, route-aware NAVIGATOR card suggester for the AI Assistant.

Given the FE's advisory UI context (current route + company/site scope), this produces the proactive
"global navigator" cards the assistant offers WITHOUT the user typing: ``explain`` (in-chat re-prompt
of the read-only chat), ``open`` (validated deep links into EXISTING native read views), and
``resume`` (the caller's own in-progress runs).

It is PURE ROUTING + AUTHZ PLUMBING, never business logic:
- Every candidate is funnelled through ``action_cards.build_action_card``, which performs the SAME
  read-only permission check the destination enforces and fail-closes (no card) on denial — so this
  module never widens scope and never discloses anything the caller couldn't already read.
- ``open`` targets are an ENUM (``OPEN_TARGET_VIEWS``); routes are derived server-side, never from
  free-form text, so a card can never point at an arbitrary/fabricated destination.
- Nothing here writes, commits, starts, advances, previews, or executes anything. Cards are inert.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.schema.assistant import AssistantActionCard, AssistantContextHints
from app.services.assistant.action_cards import build_action_card

logger = logging.getLogger(__name__)

# Hard cap so the proactive affordance stays a short, scannable list.
MAX_NAVIGATOR_CARDS = 5
# How many of the caller's own open runs to surface as resume cards.
_MAX_RESUME_CARDS = 2

# Route bucket -> (explain title, canned read-only explain prompt). The explain card re-prompts the
# read-only chat (never navigates), so the prompt is just a question the existing chat already answers.
_EXPLAIN_BY_BUCKET: dict[str, tuple[str, str]] = {
    "project_overview": (
        "Explain this project",
        "Explain the project overview page — what the key sections and status indicators mean and "
        "what I can do here.",
    ),
    "data_room": (
        "Explain the data room",
        "Explain the data room — how documents, AI-extracted fields, and the verification workflow "
        "work here.",
    ),
    "site_finance": (
        "Explain project finance",
        "Explain this project's finance summary — what the figures and sections mean.",
    ),
    "reconciliation": (
        "Explain reconciliation",
        "Explain the diligence reconciliation ladder — what its stages and statuses mean.",
    ),
    "company_hub": (
        "Explain this workspace",
        "Explain this company workspace — the Overview, Projects, Tasks, and Performance tabs and "
        "what I can do here.",
    ),
    "company_finance": (
        "Explain company finance",
        "Explain the company's portfolio finance summary — what the figures and sections mean.",
    ),
    "project_hub": (
        "Explain Project Hub",
        "Explain the Project Hub — how projects, asset management, and due diligence fit together.",
    ),
    "workflows": (
        "Explain workflows",
        "Explain guided workflows and sequences — what they are and how I start one.",
    ),
    "generic": (
        "Explain this page",
        "Explain what this page is for and what I can do here in iliOS.",
    ),
}

# Workflow Companion explain cards — surfaced ONLY when the user is inside a guided workflow run
# (``hints.run_id`` present). Each re-prompts the read-only chat with a step-aware question the
# assistant answers by grounding in the run via get_workflow_run. Inert: clicking re-asks the chat,
# it never navigates and never executes the workflow.
_COMPANION_EXPLAINS: tuple[tuple[str, str], ...] = (
    (
        "Explain this step",
        "Explain the step I'm currently on in this workflow — what it's for and what each field means.",
    ),
    (
        "What does a field mean?",
        "What does each field on the current step mean, and which ones are required?",
    ),
    (
        "Why did my entry fail?",
        "Why did my last entry on this step fail validation, and how do I fix it?",
    ),
    (
        "What happens on confirm?",
        "What will the final confirm step of this workflow do when I run it?",
    ),
)

# Bucket -> ordered ``open`` target_views to offer (each still permission-gated + scope-checked).
_OPEN_BY_BUCKET: dict[str, tuple[str, ...]] = {
    "project_overview": ("data_room", "reconciliation", "site_finance"),
    "data_room": ("project_overview", "reconciliation"),
    "site_finance": ("project_overview", "data_room"),
    "reconciliation": ("project_overview", "data_room"),
    "company_hub": ("company_finance",),
    "company_finance": (),
    "project_hub": (),
    "workflows": (),
    "generic": (),
}


def _bucket(route: Optional[str]) -> str:
    """Classify a FE pathname into a navigator bucket (longest/most-specific match wins)."""
    if not route:
        return "generic"
    r = route.split("?", 1)[0].rstrip("/").lower()
    if r.startswith("/project-hub/companies"):
        return "company_hub"
    if "/data-room" in r:
        return "data_room"
    if r.startswith("/project-hub/projects"):
        return "project_overview"
    if r.startswith("/project-hub"):
        return "project_hub"
    if r.startswith("/finance/sites"):
        return "site_finance"
    if r.startswith("/finance"):
        return "company_finance"
    if r.startswith("/reconciliation"):
        return "reconciliation"
    if r.startswith("/workflows"):
        return "workflows"
    return "generic"


def _resolve_site_id(hints: Optional[AssistantContextHints]) -> Optional[int]:
    if not hints:
        return None
    return hints.site_id if hints.site_id is not None else hints.project_id


def _open_run_ids(
    db_session: Session,
    current_user,
    *,
    site_id: Optional[int],
    company_id: Optional[int],
    limit: int,
) -> list[int]:
    """The caller's OWN open (resumable) run ids, optionally scoped to the current site/company.

    Owner-scoped via ``list_user_runs`` (read-only); closed runs are excluded. Returns ids only —
    ``build_action_card(kind='resume', run_id=...)`` re-validates each before a card is produced.
    """
    try:
        from app.models.workflow import WorkflowRunStatus
        from app.services.workflows.engine import list_user_runs

        runs = list_user_runs(db_session, current_user).items
    except Exception:  # noqa: BLE001 - resume cards are best-effort; never break suggestions
        logger.exception("navigator: listing user runs failed")
        return []

    closed = {WorkflowRunStatus.completed, WorkflowRunStatus.abandoned}
    out: list[int] = []
    for run in runs:
        if getattr(run, "status", None) in closed:
            continue
        if site_id is not None:
            if getattr(run, "site_id", None) != site_id:
                continue
        elif company_id is not None and getattr(run, "company_id", None) != company_id:
            continue
        out.append(run.id)
        if len(out) >= limit:
            break
    return out


def _collect(result: dict, sink: list[AssistantActionCard], seen: set) -> None:
    """Append a permitted card (deduped). Mirrors the chat-loop collector so the shape is identical."""
    if not (isinstance(result, dict) and result.get("permitted")):
        return
    card = result.get("action_card")
    if not isinstance(card, dict):
        return
    key = (
        card.get("kind"),
        card.get("target_view"),
        card.get("route"),
        card.get("run_id"),
        card.get("prompt"),
    )
    if key in seen:
        return
    try:
        sink.append(AssistantActionCard(**card))
        seen.add(key)
    except Exception:  # noqa: BLE001 - a malformed card must never break the navigator
        logger.warning("navigator skipped a malformed action card: %r", card)


def _build_companion_cards(
    db_session: Session,
    current_user,
    hints: AssistantContextHints,
    *,
    max_cards: int,
) -> list[AssistantActionCard]:
    """Step-aware companion cards for a user inside a guided workflow run (``hints.run_id`` set).

    Produces inert ``explain`` re-prompts (always available — they only re-ask the read-only chat)
    plus a ``resume`` card for THIS run (owner-validated + fail-closed by ``build_action_card``).
    Read-only end-to-end; nothing here starts, advances, previews, or executes the workflow.
    """
    route = hints.route
    site_id = _resolve_site_id(hints)
    cards: list[AssistantActionCard] = []
    seen: set = set()

    # Reserve the run's resume card FIRST so it can never be crowded out by explain cards — the whole
    # point of companion mode is keeping the active run one click away. It is built (and owner-
    # re-validated) up front, then appended last so explains read top-to-bottom; simply absent if the
    # run isn't resumable. Read-only: a resume card is an inert deep link, never an execution.
    resume_cards: list[AssistantActionCard] = []
    if hints.run_id is not None:
        _collect(
            build_action_card(db_session, current_user, kind="resume", run_id=hints.run_id),
            resume_cards,
            seen,
        )
    explain_budget = max(0, max_cards - len(resume_cards))

    for title, prompt in _COMPANION_EXPLAINS:
        if len(cards) >= explain_budget:
            break
        _collect(
            build_action_card(
                db_session,
                current_user,
                kind="explain",
                prompt=prompt,
                title=title,
                current_route=route,
                site_id=site_id,
                company_id=hints.company_id,
            ),
            cards,
            seen,
        )

    cards.extend(resume_cards)
    return cards[:max_cards]


def build_navigator_cards(
    db_session: Session,
    current_user,
    hints: Optional[AssistantContextHints],
    *,
    max_cards: int = MAX_NAVIGATOR_CARDS,
) -> list[AssistantActionCard]:
    """Deterministic, permission-gated navigator cards for the caller's current page.

    When the caller is inside a guided workflow run (``hints.run_id`` present) the assistant is in
    Workflow Companion Mode, so step-aware companion cards are surfaced instead of the generic page
    navigator. Otherwise: an ``explain`` card for the page, then page-relevant ``open`` deep links,
    then the caller's own resumable runs — each validated by ``build_action_card`` and fail-closed,
    then deduped and capped. Read-only end-to-end.
    """
    if hints and hints.run_id is not None:
        return _build_companion_cards(db_session, current_user, hints, max_cards=max_cards)

    route = hints.route if hints else None
    company_id = hints.company_id if hints else None
    site_id = _resolve_site_id(hints)
    bucket = _bucket(route)

    cards: list[AssistantActionCard] = []
    seen: set = set()

    # 1) Explain this page (in-chat re-prompt; available wherever the assistant is).
    title, prompt = _EXPLAIN_BY_BUCKET.get(bucket, _EXPLAIN_BY_BUCKET["generic"])
    _collect(
        build_action_card(
            db_session,
            current_user,
            kind="explain",
            prompt=prompt,
            title=title,
            current_route=route,
            site_id=site_id,
            company_id=company_id,
        ),
        cards,
        seen,
    )

    # 2) Page-relevant Open deep links (permission-gated; a denied/under-scoped one is simply absent).
    for target_view in _OPEN_BY_BUCKET.get(bucket, ()):  # noqa: B007
        if len(cards) >= max_cards:
            break
        _collect(
            build_action_card(
                db_session,
                current_user,
                kind="open",
                target_view=target_view,
                site_id=site_id,
                company_id=company_id,
            ),
            cards,
            seen,
        )

    # 3) The caller's own open runs to resume (owner-scoped), scoped to the page where possible.
    if len(cards) < max_cards:
        for run_id in _open_run_ids(
            db_session,
            current_user,
            site_id=site_id,
            company_id=company_id,
            limit=_MAX_RESUME_CARDS,
        ):
            if len(cards) >= max_cards:
                break
            _collect(
                build_action_card(db_session, current_user, kind="resume", run_id=run_id),
                cards,
                seen,
            )

    return cards[:max_cards]
