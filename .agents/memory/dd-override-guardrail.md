---
name: DD baseline-driving override guardrail (audit integrity)
description: How the DD override-rationale guardrail enforces server-side across BOTH set_key and bulk_accept_ai_values, why it fails closed, and the all-or-nothing bulk contract.
---

# Override guardrail for baseline-driving DD fields

A reviewer changing a baseline-driving field (the 16 `DueDiligenceBQKeys`) away from its AI-extracted value MUST supply an `override_notes` rationale, or the write is rejected (422). This is an audit-integrity rule: a wrong value on these fields silently propagates into expected-production / loss baselines.

## The rule lives server-side, NOT in client status
Enforcement is by VALUE DIVERGENCE, computed in `set_key`, not by the client-sent `status`. Earlier the guardrail only fired when the client sent `status="overridden"`; since status defaults to `"accepted"`, any direct API call (or the plain UI accept path) bypassed it. Never trust client status for this — resolve the AI original and compare.

**Why:** the client status is bug/attacker-controlled; the divergence fact is not.

**How it works:** `ProjectFactsService.resolve_ai_original_value(site_id, canonical_field, file_id)` returns `(determined, ai_original)` — primary source is the candidate fact's `ai_extracted_value`, fallback is the latest completed parse run (highest `extraction_run_number`). Compare via `_normalize_term` (strip + str compare). Determined + diverges → force `overridden`, require notes. Undetermined + an existing key → fail-safe compare vs `existing_key.effective_value`. Brand-new manual key with no AI evidence → allowed as accepted (not an override). Re-accept / no divergence CLEARS stale override columns on BOTH the DocumentKey and the candidate fact (the three override-provenance keys are exempted from the drop-None filter so they can be nulled while `ai_extracted_value` is preserved).

**Fails CLOSED:** `_normalize_term` is a strict post-strip string compare, so "100" vs "100.0"/"1,000" reads as divergent and demands a rationale — never silently accepted. Acceptable tradeoff (reviewer friction, not a hole).

## Shared between BOTH endpoints
`set_key` and `bulk_accept_ai_values` now both route through the same pure helper `app/helpers/due_diligence/override_guardrail.py` (`normalize_term` + `evaluate_baseline_override(...) -> OverrideEvaluation{diverges, effective_status, requires_rationale}`, no DB/no baseline calc). Keep enforcement in this one place so the two paths can never drift.

## Bulk-accept is all-or-nothing
`bulk_accept_ai_values` is two-pass: Pass 1 classifies every field with ZERO writes (benign skip if not in allowed keys; non-baseline → write-plan accepted; baseline-driving → resolve canonical + AI-original-for-run + evaluate). If ANY baseline field requires a rationale it lacks, the whole batch is rejected with a 422 `JSONResponse {message, detail, code, items}` and NOTHING is written — no partial accept. Pass 2 (writes) only runs when Pass 1 is clean; its payloads mirror set_key (accepted clears the 4 override cols; overridden stamps override_value/overridden_by_id/at/notes); per-item write exceptions still preserve the 207 partial contract.

**Why two-pass:** `BaseCRUD` commits per item, so you cannot roll back mid-write; the only way to guarantee write-nothing-on-audit-failure is to validate everything before touching the DB.

**Bulk uses a RUN-preferred AI original:** `resolve_ai_original_value_for_run(run, site_id, canonical_field, source_file_id)` prefers the parsed value of the run being accepted (authoritative for bulk), falling back to `resolve_ai_original_value`. So a stale candidate fact never overrides what the accepted run actually parsed.

**Deliberately NOT copied into bulk:** set_key's legacy DD→BQ characteristics sync stays only in set_key (flag-gated); bulk only writes the DocumentKey + candidate fact (never promotes to baseline). override_notes on a NON-baseline bulk field is intentionally dropped (status forced "accepted") — bulk preserves its existing non-baseline behavior.
