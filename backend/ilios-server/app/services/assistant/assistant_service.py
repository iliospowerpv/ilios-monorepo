"""Assistant orchestration: the bounded tool-calling loop.

Stateless (Slice 1): the caller supplies any prior turns in ``history``; nothing is persisted. The
loop asks the model, runs any requested READ-ONLY tools through ``tools.dispatch_tool`` (which applies
the guardrail), feeds results back, and returns the final natural-language reply plus a transparency
record of which tools ran. The model can never trigger a write — the only side effects available to it
are the read-only catalog, and any off-catalog/mutating request is rejected and reported, not executed.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schema.assistant import (
    AssistantActionCard,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantSource,
    AssistantToolInvocation,
)
from app.services.assistant import llm_client, tools
from app.services.assistant.guardrails import AssistantGuardrailError

logger = logging.getLogger(__name__)

# Hard ceiling on model<->tool round-trips per request (prevents loops / runaway fan-out).
MAX_TOOL_ITERATIONS = 5
# Cap a single tool result fed back into the prompt so a large envelope can't blow the context.
_MAX_TOOL_RESULT_CHARS = 14000
# Defensive cap on disclosed sources so a runaway loop can't bloat the response/persisted row.
_MAX_SOURCES = 12

# Friendly, STATIC labels for the read-only DATA tools whose use we disclose as a "source". FAQ is
# disclosed separately (per curated entry); ``propose_action_card`` is a navigation affordance, not a
# knowledge source, so it is intentionally excluded here.
_TOOL_SOURCE_LABELS: dict[str, str] = {
    "list_workflows": "Available workflows",
    "list_sequences": "Guided sequences",
    "list_my_runs": "Your workflow runs",
    "get_recommendations": "Recommended next actions",
    "get_onboarding_progress": "Onboarding progress",
    "get_onboarding_readiness": "Onboarding readiness",
    "get_orchestration_context": "Workflow orchestration context",
    "get_workflow_metrics": "Workflow metrics",
}

SYSTEM_PROMPT = """You are the iliOS Assistant, a READ-ONLY guide inside the iliOS real-estate \
investment platform. iliOS manages the lifecycle of real-estate (often solar) assets: acquisition, \
due diligence, asset management, telemetry, finance, and reporting. In the UI a "Project" is the \
same record the system calls a "Site".

Your job: help users understand the platform, explain available guided workflows and sequences, \
recommend the best next action, and explain onboarding progress and readiness — grounded in live \
data you fetch with the provided tools.

STRICT LIMITS — you are advice-only:
- You CANNOT start, advance, resume, preview, or execute any workflow or sequence.
- You CANNOT promote facts, approve/activate baselines, map/unmap devices, change weather \
declarations, or write/mutate anything.
- All of those remain the user's job, confirmed inside the relevant wizard. When the right next \
step is one of these, explain it and tell the user exactly where to do it (name the workflow and \
the route), but never imply you did it or will do it.

How to answer:
- Prefer calling a tool to get live, account-specific facts over guessing. Use answer_help_faq for \
general "what is / how do I" product questions.
- Be concise and concrete. When you recommend an action, give the reason and the route/workflow to \
use. If something is unavailable or permission-denied, say so honestly — do not invent data.
- Never claim to have performed an action. You only inform and recommend."""


def _context_preamble(req: AssistantChatRequest) -> str | None:
    ctx = req.context
    if not ctx:
        return None
    parts: list[str] = []
    if ctx.route:
        parts.append(f"route={ctx.route}")
    if ctx.company_id is not None:
        parts.append(f"company_id={ctx.company_id}")
    site_id = ctx.site_id if ctx.site_id is not None else ctx.project_id
    if site_id is not None:
        parts.append(f"site_id(project_id)={site_id}")
    if not parts:
        return None
    return (
        "UI context for this question (advisory only — still verify via tools, never assume access): "
        + ", ".join(parts)
    )


def _build_messages(req: AssistantChatRequest) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    preamble = _context_preamble(req)
    if preamble:
        messages.append({"role": "system", "content": preamble})
    for turn in req.history:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": req.message})
    return messages


def _extract_tool_calls(message) -> list[tuple]:
    """Return [(id, name, arguments_str), ...] from an SDK or namespace message object."""
    raw = getattr(message, "tool_calls", None) or []
    out: list[tuple] = []
    for tc in raw:
        fn = getattr(tc, "function", None)
        out.append(
            (
                getattr(tc, "id", None),
                getattr(fn, "name", None) if fn else None,
                getattr(fn, "arguments", None) if fn else None,
            )
        )
    return out


def _truncate(text: str) -> str:
    if len(text) <= _MAX_TOOL_RESULT_CHARS:
        return text
    return text[:_MAX_TOOL_RESULT_CHARS] + '… [truncated]"}'


def _collect_action_cards(result, sink: list[AssistantActionCard], seen: set) -> None:
    """If a tool result carries a validated, permitted action card, add it (deduped) to the
    response. Cards are propose-only deep links — recording one never executes anything."""
    if not isinstance(result, dict):
        return
    card = result.get("action_card")
    if not (isinstance(card, dict) and result.get("permitted")):
        return
    key = (
        card.get("kind"),
        card.get("workflow_id"),
        card.get("sequence_id"),
        card.get("run_id"),
        card.get("route"),
    )
    if key in seen:
        return
    try:
        sink.append(AssistantActionCard(**card))
        seen.add(key)
    except Exception:  # noqa: BLE001 - never let a malformed card break the chat
        logger.warning("AI Assistant skipped a malformed action card: %r", card)


def _collect_sources(
    name: str, result, sink: list[AssistantSource], seen: set
) -> None:
    """Record LABELS-ONLY disclosures of which knowledge sources backed this turn.

    For the FAQ tool, each curated entry returned becomes a ``faq`` source (id/question/category).
    For a successful read-only DATA tool, a single ``tool`` source with a static friendly label is
    added. Never includes raw tool payloads, and is deduped + capped so the disclosure stays small.
    """
    if len(sink) >= _MAX_SOURCES:
        return
    if name == "answer_help_faq":
        entries = result.get("results") if isinstance(result, dict) else None
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            ref = entry.get("id")
            key = ("faq", ref)
            if key in seen:
                continue
            sink.append(
                AssistantSource(
                    kind="faq",
                    label=str(entry.get("question") or ref or "Help topic"),
                    ref=str(ref) if ref is not None else None,
                    detail=(str(entry["category"]) if entry.get("category") else None),
                )
            )
            seen.add(key)
            if len(sink) >= _MAX_SOURCES:
                return
        return
    label = _TOOL_SOURCE_LABELS.get(name)
    if not label:
        return
    key = ("tool", name)
    if key in seen:
        return
    sink.append(AssistantSource(kind="tool", label=label, ref=name))
    seen.add(key)


def run_assistant_chat(
    db_session: Session, current_user, req: AssistantChatRequest
) -> AssistantChatResponse:
    messages = _build_messages(req)
    used: list[AssistantToolInvocation] = []
    action_cards: list[AssistantActionCard] = []
    sources: list[AssistantSource] = []
    seen_cards: set = set()
    seen_sources: set = set()
    reply = ""

    for _ in range(MAX_TOOL_ITERATIONS):
        response = llm_client.create_chat_completion(messages=messages, tools=tools.TOOL_SPECS)
        message = response.choices[0].message
        extracted = _extract_tool_calls(message)

        if not extracted:
            reply = getattr(message, "content", None) or ""
            break

        # Echo the assistant's tool-call turn back into the transcript.
        messages.append(
            {
                "role": "assistant",
                "content": getattr(message, "content", None),
                "tool_calls": [
                    {
                        "id": tcid,
                        "type": "function",
                        "function": {"name": name or "", "arguments": args or "{}"},
                    }
                    for (tcid, name, args) in extracted
                ],
            }
        )

        for tcid, name, args_str in extracted:
            try:
                args = json.loads(args_str or "{}")
                if not isinstance(args, dict):
                    args = {}
            except (json.JSONDecodeError, TypeError):
                args = {}

            try:
                result = tools.dispatch_tool(db_session, current_user, name or "", args)
                used.append(AssistantToolInvocation(name=name or "", ok=True))
                _collect_action_cards(result, action_cards, seen_cards)
                _collect_sources(name or "", result, sources, seen_sources)
                content = _truncate(json.dumps(result, default=str))
            except AssistantGuardrailError as exc:
                used.append(
                    AssistantToolInvocation(name=name or "", ok=False, error=str(exc))
                )
                content = json.dumps(
                    {
                        "error": "not_permitted",
                        "message": str(exc),
                        "note": "This assistant is read-only; tell the user to perform the action "
                        "manually in the relevant workflow.",
                    }
                )
            except Exception as exc:  # noqa: BLE001 - surface a safe message, never crash the chat
                logger.exception("AI Assistant tool %r failed", name)
                used.append(
                    AssistantToolInvocation(name=name or "", ok=False, error=type(exc).__name__)
                )
                content = json.dumps(
                    {"error": "tool_failed", "message": "The tool could not complete this request."}
                )

            messages.append({"role": "tool", "tool_call_id": tcid, "content": content})
    else:
        # Loop exhausted without a final, tool-free answer.
        reply = (
            "I gathered the relevant information but couldn't finish composing a full answer. "
            "Please try rephrasing your question, or check the Workflow dashboard directly."
        )

    if not reply:
        reply = "I wasn't able to produce a response. Please try rephrasing your question."

    return AssistantChatResponse(
        generated_at=datetime.now(timezone.utc),
        conversation_id=req.conversation_id,
        model=llm_client.ASSISTANT_MODEL,
        reply=reply,
        used_tools=used,
        sources=sources,
        action_cards=action_cards,
    )
