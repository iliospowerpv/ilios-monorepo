---
name: AI Assistant Workflow Companion
description: How the in-wizard Companion stays read-only and why the zero-mutation invariant holds across four layers.
---

# AI Assistant Workflow Companion

The Companion makes the existing read-only native assistant aware of the active Workflow Engine run +
current step (explain step/fields/validation/confirmation, guide resume, surface blockers). It is
purely additive on the existing assistant chat loop / tool catalog / guardrails / action-card builder.

## The invariant (must stay provably true)
The Workflow Engine is the ONLY mutator. The assistant NEVER calls `start_run` / `save_step` /
`preview_step` / `execute_step` / `execute_file` / `abandon_run` (or any governed action). Validation
errors + confirmation text are READ from the persisted run via `engine.get_run` — never produced by
calling save/preview.

**Why:** the whole feature's value depends on there being one execution path; a second path would
break governance and reconciliation guarantees.

**How to apply (4 enforcement layers — keep all four):**
1. Catalog exclusion — no engine write fn in `tools.ALLOWED_TOOLS` / `TOOL_HANDLERS` / `TOOL_SPECS`.
2. Source scan — no module under `app/services/assistant/` references any engine write-fn name
   (only reads: `get_run`, `list_user_runs`, `compute_metrics`, `list_sequences`,
   `list_workflow_definitions`).
3. Guardrail keyword screen — `guardrails.PROHIBITED_KEYWORDS` must flag all six write fns
   (`save` keyword added so `save_step` is covered; the others matched `start/preview/execute/abandon`).
4. Prompt addendum — `COMPANION_MODE_ADDENDUM` re-asserts no-execution.

## Activation & data boundary
- Companion behavior is gated ENTIRELY on `context.run_id` being present (suggested prompts switch to
  the `_COMPANION` bucket; navigator switches to `_build_companion_cards`; system addendum appended).
  Without `run_id`, route/navigator behavior is byte-for-byte unchanged — that regression guard is
  part of the test suite.
- FE wizard publishes IDENTIFIERS ONLY (`runId/workflowId/stepId/stepIndex/totalSteps`) — never
  `formValues` / `selectedFile` / `confirm_token`. Backend treats them as advisory; real run state is
  always re-fetched via owner-scoped `get_workflow_run`, so a spoofed run_id fails closed.
- Resume cards are inert deep links (`/workflows/runs/{id}`) validated via owner-scoped
  `list_user_runs`; producing a link is not a governed action.

## Known limitation (not a safety gap)
Grounding is prompt-enforced, not server-enforced: a model COULD answer without first calling
`get_workflow_run`. This is an answer-QUALITY gap only — there is no mutation risk because the only
run-state access the assistant has is the read-only tool. Candidate hardening: deterministic
server-side `get_workflow_run` injection when `context.run_id` is present.

Full design + diagrams + coverage matrix + proofs: `docs/ai_assistant_workflow_companion.md`.
Tests: `backend/ilios-server/tests/test_assistant_companion.py`.
