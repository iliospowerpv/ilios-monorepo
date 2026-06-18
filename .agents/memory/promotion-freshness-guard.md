---
name: Promotion freshness guard (fail-closed)
description: Why/how "Promote to Current Assumptions" refuses stale candidates, and the structured-409 router gotcha it exposed.
---

# Promotion Freshness Guard — fail closed

**Rule:** a candidate `project_fact` may only be promoted when its accepted *source
basis* can be proven current against the file version's CURRENT parse run (latest
by `extraction_run_number` — the SAME anchor `bulk_accept_ai_values` uses). One
stale candidate blocks the WHOLE promotion (all-or-nothing); validation is a pure
read that runs BEFORE any writes, so a blocked promotion writes nothing (no fact
promote/retire, no `AssumptionPromotion` row, `file.is_actual` untouched).

Decision matrix (per candidate): no usable current parse → all stale;
`source_run_id == current run` → FRESH (override-safe, no value compare; corruption
guard still requires the field readable); `source_run_id != current run` → stale
(`source_run_outdated`); `source_run_id` NULL (manual/single-key/legacy) → field
absent = `field_removed`, baseline-driving field = `no_lineage_baseline_field`
(blocked even when the value matches), non-baseline value-match = ALLOWED warning,
non-baseline divergence = `value_diverged_no_lineage`.

**Why baseline-driving fields are stricter:** any value that feeds expected/baseline
math (the four canonical names in `baseline_from_facts_service.FACT_FIELD_TO_COLUMN`,
exposed as `BASELINE_DRIVING_FACT_FIELDS`) must never be promoted without provable
parse lineage, even if it happens to match — lineage, not coincidence, is the gate.

## Router gotcha — structured error bodies need JSONResponse, NOT HTTPException
The app's custom `http_exception_handler` (app/utils.py) does `str(exception.detail)`,
which silently mangles a structured dict `detail` into a Python-repr string. To return
a machine-readable body you MUST `return JSONResponse(status_code=..., content={...})`
(bulk-accept guardrail does the same). The stale guard returns 409 with a TOP-LEVEL
body `{error_code: "PROMOTION_SOURCE_STALE", message, stale_fields[]}` — no `detail`
wrapper. Every other `PromotionError` keeps the legacy 400 string `detail` contract.
FE must read the top-level `message`/`error_code`, not `data.detail`, for the 409.

**Known limitation (accepted, documented):** there is no row lock between the
freshness read and the promote commit, so a reparse committing in that narrow window
could still promote against a run that just stopped being current. Closing it needs
write-path locking, which was out of scope for the additive guard.

## Test harness note
The happy-path route test creates an `AssumptionPromotion`; its `promoted_by_id` is
NOT NULL but the user FK is `ON DELETE SET NULL`, so the session-scoped auth-user
fixture teardown hits a NotNullViolation unless the test deletes the promotion rows
in a `finally`. (`project_facts.promoted_by_id` is nullable, so facts are fine.)
