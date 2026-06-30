# AI Assistant — Workflow Companion

> Status: implemented (additive, flag-gated behind `native_assistant_enabled`).
> Sibling surfaces: [`ai_assistant_global_navigator.md`](./ai_assistant_global_navigator.md),
> [`native_workflow_engine_wizard_framework_audit.md`](./native_workflow_engine_wizard_framework_audit.md).

## 1. Purpose

The native AI Assistant is already a **read-only / propose-only** helper. The Workflow Companion
turns it into an **in-wizard guide**: when a user is inside a guided Workflow Engine run, the
assistant becomes aware of the **active run + the step the user is viewing** and can:

- **Explain** the current step and what each field means.
- **Explain validation errors** the user already hit (read from the persisted run — never produced
  by re-running save/preview).
- **Explain the confirmation / execute step** before the user performs it.
- **Guide resume** of an in-progress run.
- **Surface blockers** (governed flag, prerequisites, `blocked_reason`).

### The permanent invariant

> **The Workflow Engine is the ONLY system that mutates state.**
> The assistant may **guide / explain / validate / summarize / recommend / resume-guide / deep-link**
> but it **NEVER executes**. It never calls `start_run`, `save_step`, `preview_step`,
> `execute_step`, `execute_file`, or `abandon_run` (or any other governed/write action). Every
> Companion capability wraps an **existing read service** only. Validation errors and confirmation
> text are **READ** from the persisted run via `engine.get_run`, never produced by calling a
> save/preview path.

This document includes a **zero-mutation proof** (§7) and a **no-second-path proof** (§8) that this
invariant holds, plus the test coverage matrix (§6) that pins it.

---

## 2. Architecture

The Companion is purely **additive** — it reuses the existing assistant chat loop, tool catalog,
guardrails, action-card builder, and the engine's owner-scoped read (`get_run`). The only new
runtime concept is a **UI context signal** (`run_id` / `workflow_id` / `step_id`) that flows from
the wizard to the assistant, plus one new **read-only tool** (`get_workflow_run`).

```
┌──────────────────────────────── FRONTEND (rea-investment-fe) ─────────────────────────────────┐
│                                                                                                │
│   Wizard.tsx ──publishes──▶ WorkflowCompanionContext ──consumed──▶ AssistantWidget.tsx         │
│   {runId, workflowId,        (provider mounted in            (merges run/step into chat         │
│    stepId, stepIndex,         BaseLayout, above Main          context hints + suggested-prompts │
│    totalSteps}                + AssistantWidget)              query)                            │
│        │  clears on unmount                                          │                          │
│        │  NEVER publishes formValues / selectedFile / confirm_token  │                          │
└────────┼────────────────────────────────────────────────────────────┼──────────────────────────┘
         │                                                              │  run_id / workflow_id / step_id
         ▼ (identifiers only)                                          ▼  (advisory, in API calls)
┌──────────────────────────────── BACKEND (ilios-server) ───────────────────────────────────────┐
│                                                                                                │
│  routers/assistant.py                                                                           │
│   • POST /chat              ── context.run_id present ──▶ Companion Mode                         │
│   • GET  /suggested-prompts ── run_id param present  ──▶ in_workflow=True                       │
│        │                                                                                        │
│        ▼                                                                                        │
│  services/assistant/                                                                            │
│   • assistant_service._build_messages → appends COMPANION_MODE_ADDENDUM (system turn) +         │
│        run/step preamble when run_id present                                                    │
│   • suggested_prompts.get_suggested_prompts(route, in_workflow) → _COMPANION bucket             │
│   • navigator_suggestions.build_navigator_cards → _build_companion_cards when hints.run_id set  │
│        (4 inert "explain" re-prompts + 1 fail-closed "resume" card for THIS run)                │
│   • tools.get_workflow_run(run_id) ──wraps──▶ engine.get_run (owner-scoped, READ-ONLY)          │
│   • guardrails.is_prohibited → screens every tool name against PROHIBITED_KEYWORDS              │
│        │                                                                                        │
│        ▼  READ ONLY                                                                             │
│  services/workflows/engine.get_run  ── self-authorizes via WorkflowRunCRUD.get_for_user ──▶ DB  │
│                                                                                                │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐    │
│  │  THE ONLY MUTATION PATH (NOT reachable from the assistant):                            │    │
│  │  engine.start_run / save_step / preview_step / execute_step / execute_file / abandon_run│    │
│  │  ← invoked solely by the wizard's own engine-backed endpoints (user-driven)            │    │
│  └──────────────────────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Why each piece is read-only

| Capability | Backed by | Mutation? |
|---|---|---|
| Explain step / fields / validation / confirmation / blockers | `get_workflow_run` → `engine.get_run` (serialized run state + workflow definition) | none — `get_run` is a pure read |
| Resume guidance / resume card | `build_action_card(kind="resume")` → `engine.list_user_runs` (owner-scoped) | none — produces an **inert deep link** the user clicks; clicking navigates, it does not execute |
| Companion suggested prompts | static `_COMPANION` chip list | none — pure UI affordance |
| Companion system addendum | static prompt text appended to the system turn | none — instruction text |

---

## 3. Sequence — "Explain this step" inside a wizard

```
User            Wizard.tsx        CompanionContext     AssistantWidget      /chat           assistant_service        get_workflow_run         engine.get_run (READ)
 │  opens wizard    │                    │                    │               │                    │                        │                         │
 │─────────────────▶│ publish{runId,…}──▶│                    │               │                    │                        │                         │
 │                  │                    │── context ────────▶│ (hints carry run_id/workflow_id/step_id)                    │                         │
 │ "Explain this step"                   │                    │               │                    │                        │                         │
 │──────────────────────────────────────────────────────────▶│ POST /chat ──▶│                    │                        │                         │
 │                  │                    │                    │  {message, context:{run_id,…}}      │                        │                         │
 │                  │                    │                    │               │ _build_messages: + COMPANION_MODE_ADDENDUM  │                         │
 │                  │                    │                    │               │ + "run_id=…, step_id=…" preamble            │                         │
 │                  │                    │                    │               │──── model asks for get_workflow_run ───────▶│                         │
 │                  │                    │                    │               │                    │ get_run(db,user,run_id)▶│ owner-scoped fetch ────▶│
 │                  │                    │                    │               │                    │◀── run state + defn ────│ (cross-user → 404 →     │
 │                  │                    │                    │               │                    │                        │  honest available=false)│
 │                  │                    │                    │               │◀── grounded answer (explains step/fields/validation/confirm) │
 │◀──────────────────────────────────────────────────────────│ render reply  │                    │                        │                         │
 │  closes wizard   │ clear context ────▶│                    │               │                    │                        │                         │
```

Key points:
- The assistant **reads** the run; it does not advance, save, preview, or execute it.
- Validation errors and confirmation text are whatever the engine **already persisted** — the
  Companion never triggers a save/preview to "discover" them.
- A `run_id` the caller does not own resolves to an honest `{available: false, …}` envelope with
  **no disclosure**.

---

## 4. Files changed

### Phase 1 — context hints + `get_workflow_run` tool
| File | Change |
|---|---|
| `backend/ilios-server/app/schema/assistant.py` | Added optional `workflow_id`, `run_id`, `step_id` (advisory) to `AssistantContextHints`. |
| `backend/ilios-server/app/services/assistant/tools.py` | Added `_t_get_workflow_run` wrapping `engine.get_run`; registered in `TOOL_HANDLERS`, `TOOL_SPECS`, `ALLOWED_TOOLS`. |
| `backend/ilios-server/app/services/assistant/assistant_service.py` | Added `"get_workflow_run"` source label; `COMPANION_MODE_ADDENDUM`; `_companion_addendum`; run/step preamble in `_context_preamble`; addendum wiring in `_build_messages`. |

### Phase 2 — Companion prompts / cards / endpoint params
| File | Change |
|---|---|
| `backend/ilios-server/app/services/assistant/suggested_prompts.py` | Added `_COMPANION` (6 prompts) + `in_workflow` param on `get_suggested_prompts`. |
| `backend/ilios-server/app/services/assistant/navigator_suggestions.py` | Added `_COMPANION_EXPLAINS` (4) + `_build_companion_cards`; early Companion branch in `build_navigator_cards` when `hints.run_id` is set. |
| `backend/ilios-server/app/routers/assistant.py` | `/suggested-prompts` gained `run_id` / `workflow_id` / `step_id` params; `in_workflow=run_id is not None` wiring. |

### Phase 3 — Frontend
| File | Change |
|---|---|
| `frontend/rea-investment-fe/src/contexts/workflowCompanion/workflowCompanion.tsx` (new) + `index.ts` | `WorkflowCompanionProvider`, `useWorkflowCompanion`, `usePublishWorkflowCompanion`. |
| `frontend/rea-investment-fe/src/components/layout/BaseLayout/BaseLayout.tsx` | Mounted provider (inside `SidebarProvider`) wrapping Main + AssistantWidget. |
| `frontend/rea-investment-fe/src/components/common/Wizard/Wizard.tsx` | Publishes `{runId, workflowId, stepId, stepIndex, totalSteps}`; clears on unmount. |
| `frontend/rea-investment-fe/src/components/assistant/AssistantWidget.tsx` | Merges companion context into chat context hints + suggested-prompts query. |
| `frontend/rea-investment-fe/src/api/assistant.ts` | Added `run_id` / `workflow_id` / `step_id` to `AssistantContextHints` + `getSuggestedPrompts` params. |

### Phase 4 — tests + docs
| File | Change |
|---|---|
| `backend/ilios-server/tests/test_assistant_companion.py` (new) | 22 tests across the 6 coverage areas below. |
| `docs/ai_assistant_workflow_companion.md` (this file) | Architecture + sequence diagrams, files-changed, coverage matrix, zero-mutation / no-second-path proofs. |

---

## 5. The "identifiers only" data boundary (frontend)

The wizard publishes **identifiers only** — `runId`, `workflowId`, `stepId`, `stepIndex`,
`totalSteps`. It **never** publishes `formValues`, `selectedFile`, or `confirm_token`. The backend
treats all of these as **advisory** context (the preamble explicitly says "advisory only — still
verify via tools, never assume access"); the actual run state is always re-fetched via the
owner-scoped `get_workflow_run`. This means:
- No unsaved form input ever leaves the wizard through the assistant.
- The assistant cannot be tricked into "knowing" a value the engine has not persisted.
- A spoofed `run_id` in context still hits the owner-scoped `get_run` and fails closed.

The common `<Wizard>` is used **only** by the 6 engine-backed workflow pages (AddCompany, AddSite,
GenericWorkflowStart, WorkflowRun, SequenceRunner, OnboardingOrchestrator). `TelemetryWizard` and
`ProjectImportWizard` are separate components and are intentionally **not** wired into the
Companion.

---

## 6. Test coverage matrix

All tests in `backend/ilios-server/tests/test_assistant_companion.py` (22 tests, all passing). The
full assistant suite (`phase1 + navigator + slice3 + companion`) is **114 passing, 0 regressions**.

| # | Area | Tests | Asserts |
|---|---|---|---|
| 1 | `get_workflow_run` tool | `test_get_workflow_run_catalogued_labelled_and_not_prohibited`, `…_spec_requires_run_id`, `…_happy_path_wraps_engine_get_run`, `…_missing_run_id_is_honest_unavailable`, `…_cross_user_returns_honest_unavailable_without_disclosure` | catalogued/labelled/guardrail-clean; requires `run_id`; wraps `engine.get_run`; missing id → honest unavailable + engine never called; cross-user 404 → content-free `{available:false}`; **zero writes** |
| 2 | Companion suggested prompts | `test_companion_prompts_when_in_workflow`, `…_in_workflow_overrides_route_mapping`, `…_route_mapping_unchanged_when_not_in_workflow` | `in_workflow=True` → "Workflow Companion" + 6 prompts; overrides route; route mapping unchanged when off |
| 3 | Companion navigator cards | `test_navigator_companion_mode_when_run_id_present`, `…_resume_failclosed_when_run_not_resumable`, `…_resume_failclosed_when_run_not_owned`, `…_respects_cap`, `…_falls_back_to_generic_without_run_id` | run_id → explain re-prompts lead + resume for THIS run; resume fail-closed when closed/unowned; cap honored; **no `open` cards** in Companion Mode; generic fallback without run_id; **zero writes** |
| 4 | `/suggested-prompts` endpoint | `test_suggested_prompts_endpoint_companion_with_run_id`, `…_route_mapping_without_run_id`, `…_flag_gate_applies_with_run_id` | `run_id` flips surface to Companion; route mapping preserved without it; flag gate (404) still enforced |
| 5 | Companion system addendum + chat | `test_companion_addendum_only_with_run_id`, `test_build_messages_appends_companion_turn_and_run_context`, `…_no_companion_turn_without_run_id`, `test_companion_chat_grounds_in_get_workflow_run_with_zero_writes` | addendum only with run_id; system turn + run/step preamble present; chat grounds via `get_workflow_run`; **zero writes** |
| 6 | Zero-execution / no-second-path | `test_no_engine_write_fn_is_exposed_as_a_tool`, `test_assistant_package_never_references_engine_write_fns` | no engine write fn in `ALLOWED_TOOLS`/`TOOL_HANDLERS`/`TOOL_SPECS`; source scan: no module under `app/services/assistant/` references any write fn |

Additional manual verification:
- **TypeScript**: Frontend webpack `webpack compiled successfully` + `No issues found.` (fork-ts-checker clean).
- **Auth gating (curl)**: unauthenticated `GET /api/assistant/suggested-prompts?run_id=…` → **401**;
  unauthenticated `POST /api/assistant/chat` with companion context → **401**. (The app_preview
  screenshot tool is unauthenticated and renders Sign In, so it is not a valid auth-path check; the
  401 probes + unit tests + the webpack typecheck are the verification path.)

---

## 7. Zero-mutation proof

Every Companion capability is read-only by construction:

1. **The grounding tool reads, never writes.** `tools._t_get_workflow_run` calls only
   `engine.get_run(...).model_dump(...)`. `engine.get_run` self-authorizes via
   `WorkflowRunCRUD.get_for_user` and performs a pure SELECT. On any `HTTPException` (cross-user /
   not-found) it returns `{available: false, reason: "not_authorized_or_not_found", run_id}` — no
   disclosure, no write.
2. **Every Companion unit test asserts zero writes** using a `MagicMock` DB session and
   `_assert_no_writes(db)`, which fails if any of `add / add_all / commit / flush / delete / merge /
   execute / bulk_save_objects` was called (areas 1, 3, 5 above).
3. **The chat-loop test** (`test_companion_chat_grounds_in_get_workflow_run_with_zero_writes`) drives
   a full assistant turn that dispatches `get_workflow_run` and asserts `_assert_no_writes(db)`.
4. **Resume is a deep link, not an action.** The resume card is produced by
   `build_action_card(kind="resume")`, which only reads `list_user_runs` to validate ownership and
   returns an inert route (`/workflows/runs/{id}`). Clicking it navigates the user; it never calls a
   governed action.

---

## 8. No-second-path proof

There is exactly **one** execution path — the Workflow Engine, invoked by the wizard's own
engine-backed endpoints. The assistant cannot reach it:

1. **Catalog exclusion** (`test_no_engine_write_fn_is_exposed_as_a_tool`): none of `start_run`,
   `save_step`, `preview_step`, `execute_step`, `execute_file`, `abandon_run` appear in
   `tools.ALLOWED_TOOLS`, `tools.TOOL_HANDLERS`, or `tools.TOOL_SPECS`. They are simply not callable
   tools.
2. **Source scan** (`test_assistant_package_never_references_engine_write_fns`): a test reads every
   `*.py` under `app/services/assistant/` and asserts **none** reference any engine write-fn name.
   The only engine imports in the assistant package are reads (`get_run`, `list_user_runs`,
   `compute_metrics`, `list_sequences`, `list_workflow_definitions`).
3. **Guardrail screen**: `guardrails.is_prohibited` matches tool names against `PROHIBITED_KEYWORDS`
   (`start`, `execute`, `preview`, `resume`, `abandon`, `save`, plus other write verbs) and
   `assert_tool_allowed` blocks any prohibited name before dispatch — a defense-in-depth backstop
   even if a write tool were ever added by mistake. `test_guardrail_keywords_block_every_engine_write_fn`
   pins that **all six** engine write fns (`start_run` / `save_step` / `preview_step` /
   `execute_step` / `execute_file` / `abandon_run`) are screened by these keywords.
4. **Prompt-level re-assertion**: `COMPANION_MODE_ADDENDUM` explicitly tells the model it must not
   execute and must only explain/guide — so even the instruction layer reinforces the contract.

Together, (1) removes the capability, (2) proves it is not even referenced, (3) blocks it at
dispatch, and (4) instructs the model — four independent layers all pointing the same way.

---

## 9. Gaps & limitations

- **Advisory step_id.** `step_id` is advisory context only; the authoritative current step always
  comes from `get_run`. If the FE and persisted run disagree (e.g. a stale tab), the assistant
  grounds in the persisted run, which is correct but may differ from what the user sees mid-edit.
- **Unsaved input is invisible by design.** Because the wizard never publishes `formValues`, the
  assistant cannot explain a value the user has typed but not yet saved. This is intentional (the
  data boundary in §5) — the assistant explains *persisted* state.
- **Resume scope.** The Companion resume card targets only **this** run. Cross-run resume discovery
  remains the job of the global navigator (`ai_assistant_global_navigator.md`).
- **Only the common `<Wizard>` is wired.** `TelemetryWizard` / `ProjectImportWizard` do not publish
  companion context (they are not engine-backed runs).
- **Grounding is prompt-enforced, not server-enforced.** `COMPANION_MODE_ADDENDUM` instructs the
  model to call `get_workflow_run` *first*, but nothing in the server forces that call. This is a
  *quality* guarantee (a model could in principle answer from general knowledge without grounding),
  **not a safety one** — it creates **no** mutation risk because the only run-state access the
  assistant has is the read-only tool. Hardening this into a deterministic server-side grounding
  injection is captured below as a candidate next step.

## 10. Recommended next step

Add an **opt-in "what changed since I last saved?"** read that diffs the persisted run's step inputs
against the previous persisted revision (still read-only, via `get_run` history) so the Companion can
explain validation deltas without ever touching the save path. This stays within the zero-mutation /
single-execution-path contract and is the natural extension of the explain-validation capability.
