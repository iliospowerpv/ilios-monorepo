"""Privacy-bounded, first-party UI-interaction analytics for the AI Assistant (Task #89).

This module is the ONLY writer of the isolated ``assistant_ui_events`` table, and it is a deliberate
NON-assistant write path: it is invoked exclusively by the authenticated ``POST /api/assistant/events``
ingest endpoint on a user's UI interaction. It is NEVER part of the assistant reasoning/tool/LLM loop
and is never exposed as a tool, so the permanent invariant (the assistant never mutates anything; the
Workflow Engine is the only mutator of business state) is untouched — this writes only bounded UI
telemetry, never operational/business truth.

Hard privacy boundaries enforced here:

* Event names are validated against the closed :class:`AssistantUiEventName` allowlist (the Pydantic
  layer already rejects unknown names with a 422 before we run).
* Raw client routes are normalized to a coarse, fixed bucket token with ALL entity ids discarded —
  a path is never stored verbatim.
* ``detail`` is reduced to a small, per-event allowlisted token; anything else becomes ``None``.
* ``user_id`` is taken from the authenticated caller, NEVER the client payload.
* Nothing else (no message/reply text, no business value, no entity id) is accepted or stored.

Reads are aggregate-only (:func:`build_interaction_stats`) and exposed solely through the existing
admin-gated usage endpoint; no per-user analytics is ever returned.
"""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.assistant import AssistantUiEvent, AssistantUiEventName
from app.schema.assistant import (
    AssistantActionCardClickStat,
    AssistantInteractionStats,
)

# Ordered (route-prefix, canonical-token) pairs. First match wins, so list more specific prefixes
# first. The token set is CLOSED — an unknown but present route collapses to ``_OTHER_BUCKET`` so we
# never persist an arbitrary path (and therefore never an entity id embedded in one).
_ROUTE_BUCKETS: list[tuple[str, str]] = [
    ("/project-hub", "project_hub"),
    ("/telemetry", "telemetry"),
    ("/data-room", "data_room"),
    ("/workflows", "workflows"),
    ("/acquisitions", "acquisitions"),
    ("/companies", "companies"),
    ("/due-diligence", "due_diligence"),
    ("/operations-and-maintenance", "operations_maintenance"),
    ("/finance", "finance"),
    ("/reports", "reports"),
    ("/performance", "performance"),
    # `/portfolio-admin` is a settings/admin surface; list it BEFORE `/portfolio` so the broader
    # portfolio prefix never swallows the admin route (mirrors the suggested-prompt module order).
    ("/portfolio-admin", "admin"),
    ("/portfolio", "portfolio"),
    ("/admin", "admin"),
    ("/settings", "admin"),
    ("/home", "workspace"),
    ("/workspace", "workspace"),
]
_OTHER_BUCKET = "other"

# Per-event ``detail`` allowlists. An event absent from this map admits NO detail (always nulled);
# a present event keeps the reported token only when it is in the set.
_CARD_KINDS = {"workflow", "sequence", "resume", "open", "explain"}
_ENTRY_SOURCES = {"topbar", "help_menu", "sidebar", "empty_state", "module_header"}
_HINT_KINDS = {"step_help"}
_DETAIL_ALLOWLIST: dict[AssistantUiEventName, set[str]] = {
    AssistantUiEventName.action_card_clicked: _CARD_KINDS,
    AssistantUiEventName.discoverability_entry_clicked: _ENTRY_SOURCES,
    AssistantUiEventName.proactive_hint_shown: _HINT_KINDS,
    AssistantUiEventName.proactive_hint_dismissed: _HINT_KINDS,
    AssistantUiEventName.proactive_hint_opened: _HINT_KINDS,
}

# Cap how many distinct card kinds we report (bounded; there are only five kinds today).
_CARD_CLICK_CAP = 10


def normalize_route(route: Optional[str]) -> Optional[str]:
    """Reduce a raw client route to a coarse bucket token (entity ids discarded).

    Returns ``None`` when no route was supplied, the matching canonical token when a known prefix is
    hit, or ``_OTHER_BUCKET`` for an unrecognized (but present) route. A raw path is NEVER returned.
    """
    if not route:
        return None
    normalized = route.strip().lower()
    if not normalized:
        return None
    for prefix, token in _ROUTE_BUCKETS:
        if normalized.startswith(prefix):
            return token
    return _OTHER_BUCKET


def normalize_detail(
    event: AssistantUiEventName, detail: Optional[str]
) -> Optional[str]:
    """Reduce ``detail`` to a per-event allowlisted token, or ``None`` if not permitted/known."""
    if detail is None:
        return None
    allowed = _DETAIL_ALLOWLIST.get(event)
    if not allowed:
        return None
    token = detail.strip().lower()
    return token if token in allowed else None


def record_events(db_session: Session, current_user, events: Iterable) -> int:
    """Persist a bounded batch of UI events for the authenticated caller. Returns the count stored.

    ``events`` are already Pydantic-validated (closed event allowlist, bounded batch + field
    lengths, ``extra='forbid'``). Here we additionally normalize route → bucket and detail → token,
    and stamp ``user_id`` from the authenticated user (never the payload).
    """
    rows: list[AssistantUiEvent] = []
    for ev in events:
        event = AssistantUiEventName(ev.event)
        rows.append(
            AssistantUiEvent(
                user_id=current_user.id,
                event=event,
                route_bucket=normalize_route(ev.route),
                detail=normalize_detail(event, ev.detail),
                in_companion=bool(ev.in_companion),
            )
        )
    if not rows:
        return 0
    db_session.add_all(rows)
    db_session.commit()
    return len(rows)


def build_interaction_stats(db_session: Session) -> AssistantInteractionStats:
    """Aggregate counts over ONLY the isolated ``assistant_ui_events`` table (admin-gated by caller).

    Every query is a SELECT; no per-user data is returned. The action-card breakdown groups by the
    bounded ``detail`` token (the card kind).
    """
    counts: dict[AssistantUiEventName, int] = dict(
        db_session.query(AssistantUiEvent.event, func.count())
        .group_by(AssistantUiEvent.event)
        .all()
    )

    def c(name: AssistantUiEventName) -> int:
        return int(counts.get(name, 0))

    companion_prompts = (
        db_session.query(func.count())
        .filter(
            AssistantUiEvent.event == AssistantUiEventName.prompt_submitted,
            AssistantUiEvent.in_companion.is_(True),
        )
        .scalar()
        or 0
    )

    card_rows = (
        db_session.query(AssistantUiEvent.detail, func.count())
        .filter(
            AssistantUiEvent.event == AssistantUiEventName.action_card_clicked,
            AssistantUiEvent.detail.isnot(None),
        )
        .group_by(AssistantUiEvent.detail)
        .order_by(func.count().desc())
        .limit(_CARD_CLICK_CAP)
        .all()
    )
    action_card_clicks = [
        AssistantActionCardClickStat(kind=kind, count=int(count))
        for kind, count in card_rows
    ]

    return AssistantInteractionStats(
        opens=c(AssistantUiEventName.assistant_opened),
        dismissals=c(AssistantUiEventName.assistant_dismissed),
        prompt_submissions=c(AssistantUiEventName.prompt_submitted),
        companion_prompt_submissions=int(companion_prompts),
        suggested_prompt_clicks=c(AssistantUiEventName.suggested_prompt_clicked),
        sources_disclosures_opened=c(AssistantUiEventName.sources_disclosure_opened),
        first_run_shown=c(AssistantUiEventName.first_run_shown),
        first_run_dismissed=c(AssistantUiEventName.first_run_dismissed),
        first_run_opened=c(AssistantUiEventName.first_run_opened),
        proactive_hint_shown=c(AssistantUiEventName.proactive_hint_shown),
        proactive_hint_dismissed=c(AssistantUiEventName.proactive_hint_dismissed),
        proactive_hint_opened=c(AssistantUiEventName.proactive_hint_opened),
        discoverability_entry_clicks=c(
            AssistantUiEventName.discoverability_entry_clicked
        ),
        action_card_clicks=action_card_clicks,
        events_total=sum(int(n) for n in counts.values()),
    )
