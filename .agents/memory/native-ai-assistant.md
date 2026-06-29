---
name: Native AI Assistant (read-only)
description: Architecture + hard constraints of the native AI Assistant over the Workflow Engine; what every future slice must stay consistent with.
---

# Native AI Assistant — read-only reasoning layer

The native AI Assistant (`app/services/assistant/*`, router `app/routers/assistant.py`,
`POST /api/assistant/chat`) is a **read-only / propose-only** advisor over the native Workflow
Engine. It is entirely separate from the legacy Due-Diligence chatbot (`routers/due_diligence/
chatbot.py`, external WS, `chatbot_conversations`) — share no routes/services/tables/session.

## The non-negotiable contract
The assistant may NEVER start/advance/resume/preview/execute a workflow or run, and never perform a
governed action (promote fact, activate baseline, map/unmap device, change weather declaration) or
any write. It runs **as the caller** — `current_user` is threaded straight into the wrapped services,
so authorization is delegated, never bypassed (no privileged/bypass user is ever constructed).

**Why:** the engine's whole safety model is that governed/operational mutations go only through the
human-authorized handshake endpoints; an AI that could call them would defeat it.

## How the guarantee is enforced (defense in depth)
- Tools are thin wrappers over EXISTING read-only services (engine list/metrics,
  recommendations/progress/readiness/orchestration-context builders, a local curated FAQ). Each
  returns `model_dump(mode="json")`. No tool touches `db.add/commit/...`.
- `guardrails.assert_tool_allowed(name, ALLOWED_TOOLS)` runs **two** independent checks: (1) name in
  the explicit read-only allowlist AND (2) name does not match a prohibited-keyword screen derived
  from `orchestration_context_service.PROHIBITED_ACTIONS` + generic mutation verbs.
- `tools.dispatch_tool` is the SINGLE choke point — the loop never calls a handler directly.
- The tool-calling loop is bounded by `MAX_TOOL_ITERATIONS` with a `for/else` graceful fallback; a
  model request for an off-catalog/mutating tool is rejected, recorded in `used_tools` (ok=False),
  fed back as an error, and never executed.

**How to apply (future slices):** keep this contract. Slice 2 "launch/resume" must NOT let the AI
call the engine's start/advance endpoints — surface an *action card* the user confirms (the existing
handshake), and gate advice on the TARGET action's permission, not the read permission. Adding a tool
= add it to `TOOL_HANDLERS` (allowlist derives from it) AND ensure its name passes `is_prohibited`.

## Flag + rollout
Gated by lowercase `native_assistant_enabled` (settings `case_sensitive=True`), default False →
`/api/assistant/*` returns 404. Auth dependency runs before the flag check, so unauthenticated is 401
regardless. Slice 1 is STATELESS (client supplies `history`; persistence deferred to a later slice).

## Testing
Pure unit style (no live DB): scripted fake OpenAI client (`SimpleNamespace` mimicking
`choices[0].message.tool_calls[].function.{name,arguments}`); zero-write proof = `MagicMock` db with
`add/commit/flush/delete/...` asserted not-called; patch the wrapped services as attributes of the
`tools` module (they're imported at module load, so `monkeypatch.setattr(tools, "build_recommendations", ...)`).

## Slice 2 — action cards + persistence + FE (built on Slice 1)
- **Action cards are PROPOSE-ONLY deep links, never execution.** `services/assistant/action_cards.py`
  validates eligibility through READ-ONLY engine calls (`get_definition`/`_can_start`, `list_sequences`,
  owner-scoped `list_user_runs`) and emits a card `{permitted, reason, action_card|None}` whose `route`
  points into the EXISTING workflow UI (`/workflows/start/{id}?site_id=&company_id=`, sequence
  `/workflows/sequences/{id}`, resume `/workflows/runs/{id}`). The USER clicks it; the AI never starts/
  previews/executes. `requires_user_action` is always true. The `propose_action_card` tool name was
  chosen to pass the prohibited-keyword screen (no start/execute/run/advance verbs).
  **Why:** the card is the handoff to the human handshake — putting an executable verb in the tool name
  would trip the guardrail and, worse, imply the AI can act.
- `assistant_service._collect_action_cards` aggregates cards across the tool loop and **dedupes** on
  (kind, workflow_id, sequence_id, run_id, route); returned as `action_cards` on the chat response.
- **Persistence writes ONLY the new `assistant_*` tables** (`conversation_store.py` over
  `models/assistant.py`: `AssistantConversation` + `AssistantConversationMessage`, migration `ff41`,
  down_revision `ff40`). Owner-scoped CRUD: cross-user GET = 404, list is owner-only, DELETE is
  soft-archive (204). The tool layer stays zero-write — only the router's persist path writes. Legacy
  DD `chatbot_conversations` is untouched and shares nothing.
- Chat persist path: router `resolve_or_create` + `append_turn`, echoes `conversation_id` so the FE can
  continue/resume a thread. `persist` flag (or a supplied `conversation_id`) opts a turn into storage.
- **FE** (`src/components/assistant/*`, `src/api/assistant.ts`): a global FAB + right Drawer mounted in
  `BaseLayout` INSIDE `EntityContextProvider`/`SidebarProvider` (so context hooks work), after `<Main/>`.
  Render is gated on `GET /config` success via React Query `retry:false` — when the flag is off the
  endpoint 404s and the FAB never mounts. Context hints are advisory only (route from `useLocation`,
  company/site from `useEntityContext`; Project==Site so the same id is sent as both `site_id` and
  `project_id`) and NEVER widen authz. Action-card "Open" buttons just `navigate(card.route)` — the FE
  performs no execution either. Client supplies trailing `history` (last 20 turns).
- **Verification note:** a live flag-on smoke is not feasible in dev (endpoints are auth-gated; the
  app_preview screenshot is unauthenticated so the FAB never shows). Flag-on config/chat/persistence/
  action-card/guardrail behavior is covered by `tests/test_assistant_slice2.py` (TestClient sets the
  flag); unauth gates verified live (config & chat → 401).

## Slice 3 — knowledge/UX/observability polish (additive, same contract)
Everything below is additive, flag-gated, and keeps the read-only / zero-write-tool-layer contract
(only `conversation_store` writes; only the new isolated `assistant_*` tables).
- **Error envelope is `{message, code}`, NOT `{detail}`** — the app uses a custom
  `app/utils.py::http_exception_handler` that serializes `{"message": str(detail), "code": status}`.
  Any assistant test/FE error handling must read `.message`, not `.detail`.
- **Latent header-drop fix (cross-cutting):** that handler previously discarded `HTTPException.headers`,
  so `Retry-After` (and any custom header) never reached the browser. Fixed by passing
  `headers=getattr(exception, "headers", None)` into the `JSONResponse`. **Why:** rate-limit UX (429 +
  `Retry-After`, already in CORS `expose_headers`) is meaningless if the header is stripped server-side.
  Any HTTPException that relies on response headers depends on this — don't regress it.
- **Typed LLM errors → friendly HTTP:** `llm_client` raises `AssistantRateLimitError(retry_after=N)`
  (router → 429 + `Retry-After`) and `AssistantLLMError` (router → 503); tenacity retry kept underneath.
- **Sources disclosure:** `assistant_service._collect_sources` emits `AssistantSource` for `kind=faq`
  (entry id/question/category from FAQ tool results) and `kind=tool` (friendly label per successful data
  tool, excluding `answer_help_faq`/`propose_action_card`), deduped on `(kind, ref)` and capped. Pure
  read; persisted alongside `used_tools`. `conversation_store.append_turn`'s `sources` param is
  Optional (back-compat with Slice 2 callers/tests).
- **Suggested prompts are STATIC + deterministic** — `suggested_prompts.py` is a route→prompts map with
  a generic fallback; NO data fetch, NO business logic, NO authz widening. `GET
  /api/assistant/suggested-prompts` is flag-gated + auth only.
- **Feedback** (`feedback` enum up/down + `feedback_note`, migration `ff42` down_revision `ff41`) is
  owner-scoped (`set_feedback`; cross-user = 404) and the only new write path is still
  `conversation_store`. Router echoes `message_id` so the FE can attach thumbs to the live turn.
- **Usage observability reads ONLY the isolated assistant tables** — `usage_service.py` aggregates
  conversations/messages/feedback/top-tools with zero joins to business tables; `GET
  /api/assistant/admin/usage` is flag-gated AND platform-admin-gated (`has_platform_bypass`; non-admin
  403, flag-off 404). FE `AssistantUsagePanel` mounted under Settings → "AI Assistant" tab
  (`/settings/assistant-usage`, `AdminType.system` gate).
