---
name: DD baseline-driving override guardrail (audit integrity)
description: How the DD override-rationale guardrail enforces server-side, why it fails closed, and which sibling endpoint still bypasses it.
---

# Override guardrail for baseline-driving DD fields

A reviewer changing a baseline-driving field (the 16 `DueDiligenceBQKeys`) away from its AI-extracted value MUST supply an `override_notes` rationale, or the write is rejected (422). This is an audit-integrity rule: a wrong value on these fields silently propagates into expected-production / loss baselines.

## The rule lives server-side, NOT in client status
Enforcement is by VALUE DIVERGENCE, computed in `set_key`, not by the client-sent `status`. Earlier the guardrail only fired when the client sent `status="overridden"`; since status defaults to `"accepted"`, any direct API call (or the plain UI accept path) bypassed it. Never trust client status for this — resolve the AI original and compare.

**Why:** the client status is bug/attacker-controlled; the divergence fact is not.

**How it works:** `ProjectFactsService.resolve_ai_original_value(site_id, canonical_field, file_id)` returns `(determined, ai_original)` — primary source is the candidate fact's `ai_extracted_value`, fallback is the latest completed parse run (highest `extraction_run_number`). Compare via `_normalize_term` (strip + str compare). Determined + diverges → force `overridden`, require notes. Undetermined + an existing key → fail-safe compare vs `existing_key.effective_value`. Brand-new manual key with no AI evidence → allowed as accepted (not an override). Re-accept / no divergence CLEARS stale override columns on BOTH the DocumentKey and the candidate fact (the three override-provenance keys are exempted from the drop-None filter so they can be nulled while `ai_extracted_value` is preserved).

**Fails CLOSED:** `_normalize_term` is a strict post-strip string compare, so "100" vs "100.0"/"1,000" reads as divergent and demands a rationale — never silently accepted. Acceptable tradeoff (reviewer friction, not a hole).

## REMAINING bypass — top Phase 2 item
`bulk_accept_ai_values` (`routers/due_diligence/files_parsing.py`) writes client-supplied `field.value` with status `"accepted"` and never validates it against the run's parsed value, then updates the candidate fact to the divergent number. Same audit hole on a sibling endpoint. Still requires `Diligence:edit`, so it is an audit-integrity gap, not an access-control one. Fix: validate `field.value` against the run parsed value (or route bulk-accept through the same divergence guardrail) before accepting.
