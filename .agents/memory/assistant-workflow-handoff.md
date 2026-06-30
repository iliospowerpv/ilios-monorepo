---
name: Assistant → workflow hand-off
description: How the read-only AI assistant hands off to the workflow wizard, and the run-scope vs field-prefill distinction.
---

# Assistant → workflow hand-off

The native assistant is propose-only: it returns inert action cards (deep links), never starting/
previewing/executing/mutating. Every workflow/launch card routes to ONE page —
`GenericWorkflowStartPage` (`/workflows/start/{id}?company_id=&site_id=`). That page is the single
chokepoint that must forward the card's `company_id`/`site_id` query params into the `StartRunRequest`
body, or the run is created with null scope. The card, the API client (`startRun(id, body)`), and the
backend (`StartRunRequest`, `engine.start_run` persisting `company_id`/`site_id`) all support context;
only the generic launch page can drop it. Sequence cards carry no context (sequences self-seed);
resume cards (`/workflows/runs/{id}`) reuse the run's existing scope.

**Why:** the hand-off chain looks complete end-to-end but silently drops context at the one FE page
every card lands on — easy to miss because the backend stores the fields without complaint.

**How to apply:** any new assistant launch surface or deep link must pass scope via the
`StartRunRequest` body (mirror `SequenceRunnerPage`/`OnboardingOrchestratorPage`); coerce query ids to
positive integers and drop blanks/zero/negative before forwarding.

## Run scope ≠ field prefill (non-obvious)
Setting `run.company_id`/`run.site_id` scopes the RUN ROW only. It does NOT pre-select wizard form
fields. `serialize_definition`'s `context` = collected step inputs (`_collect_inputs`), used solely to
resolve cascading select OPTIONS (e.g. project→documents→files). There is no field-value-from-run-scope
mechanism. So "context prefill" via a card means the run is scoped, not that fields appear pre-filled.
