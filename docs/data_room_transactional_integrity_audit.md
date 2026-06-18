# Data Room — Parse / Acceptance / Promotion Transactional Integrity — Audit & Design

**Status:** AUDIT & DESIGN ONLY. No code, migrations, endpoints, schema, or UI changes were made as part of this document. Everything below labelled "proposed", "recommended", or "future" is a design proposal awaiting a separate, explicitly-scoped implementation sprint.

**Scope:** The full Data Room lineage — document/file-version upload → preprocess/OCR → AI parse run → extracted values (`document_keys`) → accept/override → candidate `project_fact` → promote to active fact → draft baseline from facts → activate baseline → O&M expected-vs-actual analytics.

**Audience:** Engineering + product reviewers deciding whether and how to harden transactional integrity across the diligence-to-analytics chain.

**Backend "Site" invariant:** unchanged throughout. "Project" remains UI terminology only; all models/routes continue to use `site_id`/`Site`.

---

## 0. Executive Summary

### 0.1 The governance problem

A recent fix correctly scoped accepted values to the **viewed file version**, so a newly uploaded version no longer inherits an older version's acceptances. That closed the *cross-version* leak. A deeper, *same-version* integrity gap remains:

> If a user accepts values on a file version and then **reparses/reprocesses that same version**, the earlier acceptance does not become stale. Acceptance at the `document_keys` level is tracked **per file version**, not per **parse run** or **extraction lineage**. The accepted value silently survives a change in its own source basis.

This matters because accepted values feed candidate facts → promoted `project_facts` → baselines → expected/O&M analytics. A wrong or stale value can propagate through that chain while every screen reports "accepted / promoted / in baseline" as though it were trustworthy.

### 0.2 The hard invariant this design defends

> **If the source basis changes, downstream review/promotion state must not silently remain valid.** Upstream changes must create a new lineage, mark dependent state stale, require re-review, or create explicit supersession. Historical data must remain preserved and auditable.

### 0.3 What the audit found (the good news)

The system is **closer to this invariant than the symptom suggests**, because lineage identity already exists at two of the four layers:

1. **Parse runs are first-class and immutable.** Every (re)parse creates a **new** `AIParsingResult` row with an incremented `extraction_run_number`; prior runs are **retained**, never overwritten. Run identity, schema version, and prompt version are all recorded.
2. **Candidate facts can carry parse-run lineage — but it is nullable and not guaranteed.** `ProjectFact` has the columns `source_run_id` (FK → `ai_parsing_results`), `source_file_id`, `source_document_key_id`, **and** `ai_extracted_value`. However, `create_candidate_from_document_key(..., run=None)` sets `source_run_id` **only when a run is passed**: the **bulk-accept** path passes the accepted run (so `source_run_id` is populated), but the single-key `set_key` / manual / per-field accept path calls it with `run=None`, leaving `source_run_id` **NULL**. Legacy candidates created before this column also have NULL. So a candidate fact *may* know which run produced it, but a freshness design must treat `source_run_id` as best-effort, not a guarantee.
3. **The acceptance layer already blocks accepting from a non-latest run** (`bulk_accept_ai_values` returns `409` unless `allow_accept_non_latest=true`; the UI defaults this to `false` and disables acceptance from a non-latest/failed run).
4. **Facts and baselines are effective-dated and supersession-aware.** `project_facts` has `effective_from`/`effective_to`/`superseded_by_fact_id`; baselines are versioned, one-active per `(site, baseline_type)`, never auto-activated, and physics constants are snapshotted immutably at creation.
5. **Reconciliation is strictly read-only** and already emits an `active_baseline_outdated` warning when an active fact changed after the baseline that consumed it.

### 0.4 What the audit found (the three real gaps)

| # | Gap | Where | Consequence |
|---|-----|-------|-------------|
| **G1** | `document_keys` has **no run linkage** and no staleness marker. The Data Room display (`combine_user_ai_parsing_results`) joins the accepted key to `file.latest_ai_result` but never compares *which run* the acceptance came from. | `document_keys` model; `app/helpers/files/file_helper.py` | After a reparse that changes a value, the old accepted value still renders as "accepted"; "Accept All" can show completed against a run the reviewer never saw. |
| **G2** | **Promotion performs no freshness re-check.** `PromotionService.promote_version` promotes *whatever candidate facts exist* for the `file_id`, without verifying each candidate's `source_run_id` is still the latest succeeded run. | `app/services/promotion_service.py` | A candidate accepted from run 1 can be promoted to an active fact even though the same file version was reparsed to run 2 with a different value. |
| **G3** | **O&M expected is compute-on-read against the *current* active baseline**, not the baseline effective for the analytics period. | `app/services/telemetry/expected_service.py`, `app/helpers/telemetry/v2_chart_data.py` | Activating a new baseline silently changes the "expected" line for *past* periods the next time a chart loads. Historical analytics are not period-pinned. |

> Note on G3 vs. the constraints: the system does **not persist** historical analytics (it recomputes on read), so nothing is *rewritten in storage*. But the *displayed* historical expected is not stable across a baseline activation, which violates the principle "O&M analytics before the effective date should remain tied to the then-active baseline." The baseline content itself is immutable; the **selection logic** is not period-aware.

### 0.5 Recommendation in one line

Adopt a **field-level source-basis fingerprint** (hybrid policy), persist run lineage on `document_keys` (the columns exist on `project_facts` but are only reliably populated on the bulk-accept path — see §0.3.2), add a **promotion freshness guard** that fails closed, surface **stale statuses** in the Data Room and Reconciliation, and make **expected/O&M selection period-effective**. Sequence it so the cheapest, highest-leverage guard (promotion freshness, which can partly reuse the existing `source_run_id` and fails closed where it is NULL) lands first and the storage-heavier work (period-effective analytics) lands last.

---

## 1. Goal, Constraints & Non-Goals

### 1.1 Strategic objective
Design a durable transactional-integrity model for Data Room parsing, acceptance, candidate facts, promotion, baselines, and downstream O&M analytics, anchored on the §0.2 hard invariant.

### 1.2 Hard constraints (carried verbatim from the request)
- Do **not** delete historical accepted values, `project_facts`, baselines, or O&M analytics.
- Do **not** make reparsed values automatically active; do **not** auto-promote; do **not** auto-create or auto-activate baselines.
- Do **not** use `SiteAdditionalFieldList` (SAFL) as a baseline source.
- Do **not** reintroduce BigQuery / Firestore / legacy telemetry.
- Do **not** change expected-calculation math, telemetry ingestion, WeatherResolver, or device eligibility.
- Do **not** touch plaintext secrets.
- Preserve auditability, effective dates, supersession, and provenance.

### 1.3 Non-goals
- No implementation in this document.
- No field-level *promotion* endpoint (promotion stays file-version-scoped and all-or-nothing — see §9 and `promote_from_reconciliation_audit.md`).
- No new acceptance surface outside the Data Room (Reconciliation stays read-only + the existing promote/task action layer).
- No change to the two distinct "expected" notions (PVsyst design-estimate vs. weather-adjusted physics) — see `telemetry-expected-baseline-design` memory.

---

## 2. Current Workflow Audit (Area A — lineage map)

### 2.1 Per-step identity & mutability

| Step | Model / Table | Identity boundary | Mutable? | Timestamps / effective dates | Supersession / stale markers | What happens on reparse |
|------|---------------|-------------------|----------|------------------------------|------------------------------|-------------------------|
| Upload document | `Document` / `documents` | site + section | Mutable | created_at / updated_at | `is_archived` | unchanged |
| Upload file version | `File` / `files` | document; new row per version | Effectively immutable (new version on re-upload) | created_at / updated_at | `is_actual`, `deleted` | a *new file version* is a different row (already handled) |
| Preprocess / OCR | (no dedicated table; handled inside parsing) | file version | n/a | n/a | n/a | re-runs as part of a new parse run |
| AI parse run | `AIParsingResult` / `ai_parsing_results` | **file version + run** | **Immutable (new row per run)** | start_time / end_time, created/updated | `extraction_run_number` (monotone), `status` (`queued`…`completed`) | **new row, prior runs retained** |
| Extracted value / acceptance | `DocumentKey` / `document_keys` | **document + file version + name** (`_document_key_version_uc`) | **Mutable in place** | created_at / updated_at | `status` (proposed/accepted/overridden); override_* cols; **NO run linkage** | **existing key persists unchanged**; no staleness signal |
| Candidate fact | `ProjectFact` (status=candidate) / `project_facts` | site + canonical_field; lineage to file/run/key | Mutable until promoted | created_at / updated_at; accepted_at / overridden_at | **`source_run_id`, `source_file_id`, `source_document_key_id`, `ai_extracted_value`** | candidate retained; still points at the run it came from |
| Active fact | `ProjectFact` (status=active) | site + canonical_field | New version on promote; old retired | `effective_from` / `effective_to` | `superseded_by_fact_id` / `supersedes_fact_id` | unaffected until an explicit promote |
| Draft baseline | `TelemetryExpectedBaseline` (status=draft) + `…_points` | site + baseline_type + version | Draft mutable; immutable once approved/active | created_at; `active_from`/`active_to` on activate | `version`, `status`, `source_fact_signature` | unaffected (no auto-build) |
| Active baseline | `TelemetryExpectedBaseline` (status=active) | one-active per `(site, baseline_type)` | Immutable snapshot | `active_from` / `active_to` | `status=superseded` on replacement | unaffected (no auto-activate) |
| O&M expected vs actual | computed on read (`expected_service`, `v2_chart_data`) — not stored | site (window) | n/a (recomputed each read) | n/a | n/a | uses **current** active baseline for all periods |
| Promotion audit | `AssumptionPromotion` / `assumptions_promotions` | site + file version | Append-only | created_at | n/a | new record per promote |

### 2.2 The identity-boundary mismatch (root of the problem)

The lineage **narrows then widens** its source-basis awareness:

```
parse run (run-aware)  →  document_key (run-BLIND)  →  candidate fact (run-aware*)  →  active fact  →  baseline
        ▲                         ▲                              ▲
   knows run_id            knows ONLY file_id        knows source_run_id *when accepted
                           (the staleness blind spot)  via a run (bulk); NULL on set_key/manual/legacy
```

- The **`document_keys` layer is the blind spot**: it is the human-acceptance record, yet it cannot say which run it accepted. The Data Room display is built here, so the "Accept All / Accepted" state is computed without run awareness (G1).
- The **candidate-fact layer can re-acquire run awareness** (`source_run_id`), but only when accepted via the bulk path; the single-key `set_key`/manual path leaves it NULL, and **promotion never reads it for freshness regardless** (G2).
- The **analytics layer** discards period awareness by always selecting the current active baseline (G3).

### 2.3 Key code references (current behavior)
- Display join: `app/helpers/files/file_helper.py::combine_user_ai_parsing_results` (scopes keys to `file_id == file.id OR file_id IS NULL`; joins to `file.latest_ai_result`).
- Single accept/override: `app/routers/due_diligence/documents.py::set_key` (writes `DocumentKey` with `file_id`; no `run_id`).
- Bulk accept + non-latest-run guard: `app/routers/due_diligence/files_parsing.py::bulk_accept_ai_values` (`allow_accept_non_latest`, `get_latest_run_for_file`, `409` on stale run).
- Candidate creation + provenance: `app/services/project_facts_service.py::create_candidate_from_document_key(..., run=None)` (always sets `source_file_id`, `source_document_key_id`, `ai_extracted_value`; sets `source_run_id` **only when a `run` is passed** — bulk-accept passes the run, `set_key`/manual/per-field accept passes `run=None`).
- Override guardrail: `app/helpers/due_diligence/override_guardrail.py` (value-divergence, fails closed, shared by both accept paths).
- Promotion: `app/services/promotion_service.py::promote_version` / `_promote_candidate_facts` (**no freshness check**).
- Reconciliation (read-only ladder): `app/services/due_diligence/reconciliation_service.py::build_site_reconciliation`.
- Baseline from facts (draft-only): `app/services/telemetry/baseline_from_facts_service.py::create_draft_from_facts`.
- Baseline lifecycle: `app/crud/telemetry_expected.py` (`get_active`, `approve`, `activate`, supersede).
- Expected compute-on-read: `app/services/telemetry/expected_service.py::compute_site_expected`, `BaselineParams.from_baseline`; chart binding `app/helpers/telemetry/v2_chart_data.py::_active_baseline`.

---

## 3. Reparse / Preprocess Behavior Audit (Area B)

Answers to the twelve scenarios, **as the system behaves today**:

1. **Reparse same file version after values were accepted.** A new `AIParsingResult` (run N+1) is created. The accepted `DocumentKey` rows are untouched and still render as accepted. No staleness is flagged anywhere. *(Gap G1.)*
2. **Reparse returns identical values.** Same as (1). The system cannot tell "identical" from "changed" at the key level because it stores no run linkage/fingerprint on the key. The accepted state persists, which *happens to be correct*, but for the wrong reason (no verification).
3. **Reparse changes one extracted value.** The new value lives only in run N+1's `parsed_result`. The accepted `DocumentKey` still shows the **old** value as accepted. The reviewer is not told the source changed. *(Core governance defect.)*
4. **Reparse removes a previously extracted field.** Run N+1 has no value for the field; the old accepted `DocumentKey` persists as accepted. Reconciliation will not show "source removed". *(Silent stale.)*
5. **Reparse adds a new field.** Run N+1 surfaces a new extracted value with no `DocumentKey`; it appears as `ai_extracted_only`/unreviewed in Reconciliation. This case is **handled acceptably** today (new value is simply unreviewed).
6. **Canonical mapping changes.** Extraction-registry mapping changes which canonical field a parsed key maps to. Existing candidate facts/keys are not re-evaluated. No fingerprint captures the mapping version. *(Stale risk, currently invisible.)*
7. **Parser/schema version changes.** `AIParsingResult` records `schema_version_id`/`prompt_template_id`, so the *run* is distinguishable, but nothing downstream compares schema versions to invalidate prior acceptance. *(Stale risk, detectable but unused.)*
8. **Accepted values already created candidate facts.** Candidate facts created via bulk-accept carry `source_run_id` (those from single-key `set_key`/manual accept do not — it is NULL). After a reparse, the candidate still points at the old run (or has no run pointer at all); it is not marked stale. *(Gap; the lineage to detect it exists only for the bulk-accept path — the rest must rely on a future `document_keys` fingerprint or fail closed.)*
9. **Those candidate facts were promoted.** Promotion proceeds with no freshness re-check (G2). The active fact then has `effective_from` and an audit record, but may encode a value the latest run no longer supports.
10. **Promoted facts already used in a draft baseline.** The draft baseline stored a `source_fact_signature`. A reparse does not invalidate the draft; Reconciliation may later show `active_baseline_outdated` only if the *fact* changed after the baseline, not if the *source run* changed under the fact.
11. **Promoted facts already used in an active baseline.** Active baseline is an immutable snapshot — correctly **not** rewritten. But there is no signal that the fact's source basis is now stale; the baseline keeps driving expected with a value whose provenance silently drifted.
12. **Active baseline values already produced O&M analytics.** Analytics are compute-on-read against the current active baseline (G3). There are no stored historical outputs to corrupt, but the displayed historical expected will shift if/when a new baseline is activated.

---

## 4. Transactional Integrity Risk Register

| ID | Risk | Likelihood | Impact | Current mitigation | Residual |
|----|------|-----------|--------|--------------------|----------|
| R1 | Stale accepted value survives reparse and reads as trustworthy | High (any reparse after accept) | High (feeds facts/baseline) | None at key layer | **Open (G1)** |
| R2 | Stale candidate promoted to active fact | Medium | High (active assumption is wrong) | Acceptance blocks non-latest run, but promotion doesn't re-check | **Open (G2)** |
| R3 | Removed field still reads as accepted | Medium | Medium | None | **Open** |
| R4 | Canonical-mapping / schema-version change not reflected in prior acceptance | Low–Med | Medium | Run records versions, but unused downstream | **Open** |
| R5 | Historical expected silently changes on baseline activation | Medium | High (audit/trust) | Baseline immutable; selection not period-aware | **Open (G3)** |
| R6 | Reviewer accepts a value they never saw (Accept All over a new run) | Medium | High | UI requires latest+successful run to accept; but display can pre-show old accepted as done | **Partial** |
| R7 | Loss of historical fact/baseline | Low | High | Effective dating + supersession + immutable baselines | **Mitigated** |
| R8 | Auto-promotion / auto-activation | Low | High | Explicitly never auto — human sign-off mandatory | **Mitigated** |

---

## 5. Recommended Lineage / Source-Basis Fingerprint Model (Areas C + D)

### 5.1 Vocabulary (canonical terms for the codebase)
- **Current parse run** — the latest `AIParsingResult` for a file version with `status=completed` (highest `extraction_run_number`).
- **Stale parse run** — any completed run that is not the current run for its file version.
- **Accepted value** — a `DocumentKey` with `status` accepted/overridden.
- **Stale accepted value** — an accepted `DocumentKey` whose source basis (run/schema/prompt/mapping/value/evidence) no longer matches the current run's value for that field.
- **Candidate fact** — `ProjectFact` with `status=candidate` (carries `source_run_id`).
- **Active fact** — `ProjectFact` with `status=active`, `effective_from` set.
- **Superseded fact** — `ProjectFact` with `status=retired`, `effective_to` + `superseded_by_fact_id` set.
- **Draft / active / superseded baseline** — `TelemetryExpectedBaseline` lifecycle states.
- **Historical analytics period** — a time window whose then-active baseline differs from the current active baseline.
- **Source-basis fingerprint** — a deterministic hash identifying the exact extraction basis behind an accepted value (definition below).

### 5.2 Source-basis fingerprint — proposed definition

A **field-level** fingerprint computed at acceptance time and stored alongside the accepted value:

```
fingerprint = sha256(normalize(
  document_id, file_id, file_version_id,
  parse_run_id, extraction_run_number,
  schema_version_id, prompt_template_id, ai_model_identifier,
  canonical_field_key,
  normalized_extracted_value,           # the AI value the human acted on
  evidence_locator                      # page / snippet hash / bbox when available
))
```

Notes:
- `normalize()` reuses the existing `normalize_term` (strip + string compare) from the override guardrail so divergence semantics are identical across accept/override/freshness checks (fails closed on `"100"` vs `"100.0"`).
- The **accepted/override value** is *not* part of the fingerprint of the *source basis* — the source basis describes what the AI produced; the human's accepted value is recorded separately so we can answer "did the *source* change?" independently of "did the *human's choice* change?".
- Much of the input already exists: `AIParsingResult` has run/schema/prompt; `ProjectFact` stores `ai_extracted_value` and (on the bulk-accept path only) `source_run_id`. Because `source_run_id` is nullable/not guaranteed at the fact layer, the **authoritative new storage** is putting the fingerprint **and** `source_run_id` on `document_keys` (the human-acceptance record), so freshness can be evaluated for *every* accepted value regardless of which accept path created it.

### 5.3 Detection options & recommendation

1. **Strict invalidation on any new parse run** — mark every accepted key on a file version stale the moment a new run completes. *Safest, simplest; noisy (re-review even when nothing changed).*
2. **Field-level fingerprint comparison** — recompute the fingerprint of the current run per field and compare to the stored one. *Precise; retains acceptance when truly unchanged.*
3. **Hybrid** — fingerprint-compare per field, with explicit outcomes: identical value+evidence ⇒ retain (audit note); changed value/evidence/schema ⇒ stale/review; removed field ⇒ stale-missing review; added field ⇒ new unreviewed.

**Recommendation: Option 3 (hybrid), with a fail-closed fallback to Option 1 for baseline-driving fields when a fingerprint cannot be computed** (e.g., evidence missing, schema version unknown). Rationale: hybrid avoids re-review churn on identical reparses (the common case) while guaranteeing the baseline-driving 16 fields never silently retain acceptance across an unverifiable source change. This mirrors the existing override guardrail philosophy (precise where possible, fail-closed on the high-impact fields).

---

## 6. Required State Transitions (Area E)

For each event, the **expected** future behavior (design target):

| Event | Accepted value | Candidate fact | Active fact | Baseline / O&M | Audit |
|-------|----------------|----------------|-------------|----------------|-------|
| Same version reparsed, **no material change** (fingerprint matches) | Remains valid; flagged `validated_against_run N+1` | Unchanged | Unchanged | Unchanged | Log reparse + "validated, no change" |
| Same version reparsed, **value changed** | Old accepted value becomes **historical/stale for current run**; new value requires review | Candidate **not** silently updated; marked `candidate_stale` | **Not** silently changed | Unchanged until explicit re-review→promote | Log reparse + diff |
| Same version reparsed, **field removed** | Prior accepted value becomes **stale-missing in current parse context** | Candidate flagged `candidate_stale` (source removed) | Unchanged | Unchanged | Log reparse + "source removed" |
| Same version reparsed, **field added** | New value is **unreviewed** | None until accepted | — | — | Log new extracted field |
| **New file version uploaded** | New version starts **unaccepted**; old version's acceptances remain **historical** | Per version | — | — | Existing behavior (already fixed) |
| **Accepted value changed / overridden** | Old accepted value is historical; new accepted/override creates a **new candidate lineage** | New candidate; promotion required to activate | — | — | Override guardrail rationale enforced |
| **Active fact superseded** | — | — | Old fact gets `effective_to`/`superseded_by`; new fact gets `effective_from` | Historical baseline/analytics remain tied to old fact for prior periods | Promotion audit record |
| **Baseline rebuilt after new facts** | — | — | — | New **draft** baseline; old active stays active until explicitly superseded; old analytics remain historical | Baseline version + signature |

The two non-negotiable lines: **a source-basis change never silently keeps downstream state valid**, and **historical artifacts are preserved (new lineage, not mutation)**.

---

## 7. Data Room UX Design (Area G)

Design targets for the `DocumentModal` after a reparse/preprocess that changes the source basis:

1. **Separate "current parse values" from "prior accepted values".** Show the latest run's extracted values as the working set; show prior acceptances clearly labelled as historical when their fingerprint no longer matches.
2. **Label stale accepted values explicitly** (chip: "Accepted from a previous parse — re-review"). Never render a stale value in the plain "Accepted/completed" state.
3. **`Accept All` operates only on the current file version AND current parse run/source basis.** (Acceptance already enforces latest+successful run; the display must stop counting stale keys as "already accepted" so the button reflects real, current work — this is the direct fix for the reported symptom at G1.)
4. **Provide a first-class "Re-review" action** per stale field and a batch "Re-review changed fields" affordance.
5. **If values changed, require explicit accept/override again** (override-rationale guardrail still applies to baseline-driving fields).
6. **If values are identical and fingerprint matches, optionally preserve accepted state with an audit note** ("validated against run N+1, unchanged") rather than forcing busy-work re-review.
7. **`Promote` only operates on the current accepted candidate lineage** (see §9); when a candidate is stale, the promote affordance is disabled with an explanatory caption, not hidden.
8. **Never silently mark stale values accepted** — honesty over convenience, consistent with the platform's "never fabricate" stance.

---

## 8. Reconciliation UX Design (Area F)

Reconciliation stays **strictly read-only** (it must never become a second acceptance surface). The ladder gains additive **stale-aware statuses** layered on the existing most-advanced-stage-wins logic. Proposed statuses:

| Status | Label | Explanation | Required action | Blocking level | Promote allowed? | DR re-review? | Create task? |
|--------|-------|-------------|-----------------|----------------|------------------|---------------|--------------|
| `stale_accepted_value` | "Accepted value is stale" | Accepted value's source run changed since acceptance | Re-review in Data Room | `blocks_baseline` (if baseline-driving) else `lowers_confidence` | **No** | **Yes** | Yes |
| `accepted_from_previous_parse` | "Accepted from earlier parse" | Accepted, but a newer parse exists (value may match) | Validate or re-review | `lowers_confidence` | Only if fingerprint matches | Optional | Yes |
| `source_changed_review_required` | "Source changed — review required" | Current run value differs from accepted | Re-accept/override new value | `blocks_baseline`/`blocks_expected` | **No** | **Yes** | Yes |
| `source_removed_review_required` | "Source removed — review required" | Field no longer extracted in current run | Confirm retain or retire | `blocks_baseline` | **No** | **Yes** | Yes |
| `candidate_stale` | "Candidate is stale" | Candidate fact points at a superseded run | Re-review then re-accept | `blocks_expected` | **No** | **Yes** | Yes |
| `active_fact_from_stale_source` | "Active fact from stale source" | Active fact's source basis drifted after promotion | Re-review; consider re-promote | `lowers_confidence` | n/a (already active) | **Yes** | Yes |
| `baseline_uses_superseded_fact` | "Baseline uses superseded fact" | Active baseline consumes a fact later superseded | Rebuild/activate new baseline (deliberate) | `blocks_reporting` | n/a | No | Yes |
| `historical_only` | "Historical only" | Only retired facts / prior versions remain | Informational | `informational` | No | No | Optional |

**Hard rule:** if the accepted source basis is stale, **promotion is blocked** (frontend convenience gate + authoritative backend guard in §9) until the value is re-reviewed in the Data Room.

This extends — does not replace — the current ladder (`in_active_baseline` > `in_draft_baseline` > `active_fact` > `accepted_not_promoted` > `candidate_only` > `accepted_document_value` > `ai_extracted_only` > `superseded` > `missing`) and the existing `active_baseline_outdated` warning.

---

## 9. Promotion Freshness Guard Design (Area H)

**Requirement:** before promoting, the backend must validate that each candidate fact being promoted is still tied to the **current accepted source basis** (current parse run, or a fingerprint that provably matches).

Proposed behavior for `PromotionService.promote_version` (still file-version-scoped, all-or-nothing — no field-level promote):

1. For every candidate fact on the file version, resolve the current completed run for `source_file_id` and compare `candidate.source_run_id` (and/or the `document_keys` fingerprint) to it.
2. **Null/legacy/manual candidates (no `source_run_id`) cannot be proven fresh and must FAIL CLOSED** — treat them as stale and require re-review. Once the §5 fingerprint lands on `document_keys`, freshness for these can be re-established by fingerprint match against the current run; until then, the conservative block applies. This is why the guard's freshness signal must be sourced from the human-acceptance record (`document_keys`), not solely from the best-effort `ProjectFact.source_run_id`.
3. **If any candidate is stale → block the whole promotion** (two-pass, mirroring `bulk_accept_ai_values`): classify first, write nothing if any field is stale.
4. Return a **structured `409`** (machine-readable list of stale fields), not a flattened `HTTPException.detail` string — same pattern the override guardrail and baseline bridge already use, so the UI can render which fields need re-review.
5. The user must re-review in the Data Room (re-accept against the current run) before promotion is allowed.

**Promotion confirmation dialog must show:** file version, parse run / source-basis version, whether each accepted value is current or stale, the **full, live-refetched diff (blast radius)**, and an explicit "the active baseline / expected math was NOT updated" note (carried over from `promote_from_reconciliation_audit.md`).

This guard is the **highest-leverage, lowest-cost** fix because it can ship a *fail-closed* first cut immediately: where `candidate.source_run_id` is populated (bulk-accept path) it compares directly; where it is NULL (single-key/manual/legacy) it blocks pending re-review. The precise, low-friction version (retain acceptance when the fingerprint provably matches) follows once `document_keys` gains the §5 fingerprint column.

---

## 10. Baseline & O&M Historical Integrity Design (Area I)

### 10.1 Current state vs. principle
- Promoted facts **are** effective-dated. ✅
- Rebuilt baselines create **new versions**; activation supersedes the prior active one; physics constants are snapshotted immutably. ✅
- Nothing auto-creates or auto-activates a baseline. ✅
- **Gap (G3):** weather-adjusted expected is recomputed on read using the **current** active baseline for **all** periods, so activating a new baseline changes historical expected. The design-estimate points are stored, but the live weather-adjusted curve is not period-pinned.

### 10.2 Design targets
1. **Period-effective baseline selection.** Expected/O&M for a bucket should use the baseline whose `active_from … active_to` covers that bucket, not unconditionally the current active one. Baselines are already effective-dated, so this is primarily a *selection* change (no new storage) — but it is math-adjacent, so it must be implemented under strict regression tests proving the live formula is unchanged (only the chosen baseline differs by period).
2. **Activating a new baseline must not rewrite historical outputs.** With period-effective selection, past periods keep their then-active baseline automatically.
3. **Explicit, audited, period-scoped backfill only.** Any deliberate recomputation of history (e.g., correcting a wrong historical baseline) must be an explicit, logged, period-bounded action — never an implicit side effect of activation.
4. **O&M after activation uses the new active baseline** for periods on/after its `active_from`.

### 10.3 Honesty contract preserved
All never-fabricate states stay intact: `baseline_not_available`, `missing_inputs`, `pre_pto` ⇒ expected = NULL (never 0). Period-effective selection must keep these semantics per bucket.

> **Constraint check:** §10 touches selection logic that feeds expected math. Per §1.2 ("do not change expected-calculation math"), the *formula* stays byte-identical; only *which immutable baseline snapshot* is selected per period changes. This must be gated behind the most rigorous test bar in the plan (§12) and is deliberately sequenced **last**.

---

## 11. Hard Platform Constraint (Area J)

Add the following as a durable platform rule (and to future implementation prompts):

> **Never allow accepted, promoted, baseline, or O&M state to silently survive upstream source changes. Upstream changes must create a new lineage, mark dependent state stale, require re-review, or create explicit supersession. Historical data must remain preserved and auditable.**

Corollaries:
- New lineage over mutation; supersession over deletion.
- Fail closed on baseline-driving fields when freshness cannot be proven.
- Read-only audit surfaces (Reconciliation) never acquire write paths beyond the existing promote/task action layer.
- No fabricated values; no legacy data path (BigQuery/Firestore); SAFL is never a baseline source.

---

## 12. Phased Implementation Recommendation (Area K)

Each phase is independently shippable and ordered by leverage-per-risk. **This document is Phase 1.**

| Phase | Deliverable | Risk | Backend files (likely) | Frontend files (likely) | Tests | Non-goals |
|-------|-------------|------|------------------------|-------------------------|-------|-----------|
| **1** | This audit + risk register (lineage map) | None | docs only | — | n/a | no code |
| **2** | Source-basis fingerprint model + `source_run_id`/fingerprint on `document_keys` (additive, nullable migration) | Low | `models/document.py`, accept paths (`documents.py`, `files_parsing.py`), `helpers/due_diligence/override_guardrail.py` | — | migration + fingerprint unit tests | no behavior change yet |
| **3** | Stale-state detection on reparse (compute current-vs-accepted fingerprint) | Med | `file_helper.py`, `project_facts_service.py`, a freshness helper | — | reparse-changed/identical/removed/added | no UI yet |
| **4** | Data Room stale-value UI (separate current vs historical, re-review action; `Accept All` excludes stale) | Med | parsing-result response additive fields | `DocumentModal.tsx`, `DocumentTermUserInputField.tsx` | component + acceptStatus tests | no Reconciliation change |
| **5** | Reconciliation stale-status ladder (additive statuses §8) | Med | `reconciliation_service.py` | `ReconciliationTable.tsx`, `StatusCell`, `utils.ts` | ladder unit tests (read-only invariant) | no writes |
| **6** | **Promotion freshness guard** (fail-closed, structured 409) | Med-High | `promotion_service.py`, promote diff/confirm | promote dialog (`usePromoteVersion`) | stale-blocks / current-allows | no field-level promote |
| **7** | Candidate-fact lineage enforcement (consistency: candidate always carries valid `source_run_id`) | Low-Med | `project_facts_service.py` | — | candidate lineage tests | no retro-backfill of old facts beyond audited script |
| **8** | Baseline effective-date / period-effective O&M selection + historical confirmation | **High** | `expected_service.py`, `v2_chart_data.py`, baseline CRUD selection | chart data hooks | golden-master expected tests proving formula unchanged | no formula change, no auto-activate |
| **9** | Tests + regression suite (full matrix §13) | Low | tests | tests | full suite | — |
| **10** | Documentation + hard-constraint updates (`replit.md`, memory, RUNBOOK) | None | docs | — | n/a | — |

Sequencing rationale: Phase 6 (promotion guard) delivers the biggest integrity win early because it can ship a fail-closed first cut on the existing (best-effort) `source_run_id` — blocking where it is NULL — and tighten once the Phase 2/3 fingerprint exists; Phase 8 (period-effective analytics) is highest risk and math-adjacent, so it lands last behind the strongest tests. (Phase 7's "candidate always carries valid `source_run_id`" includes threading the accepted run through the single-key `set_key` path, which today passes `run=None`.)

---

## 13. Tests to Design (Area L)

- New file version does **not** inherit accepted values (regression-guard the recent fix — already covered by `tests/unit/due_diligence/file_version_scoping_test.py`).
- Same file reparse with **changed** value invalidates current accepted state (→ `source_changed_review_required`).
- Same file reparse with **identical** value preserves/validates state per the hybrid policy (audit note, no forced re-review).
- **Removed** field → stale/missing status.
- **Added** field → unreviewed status.
- `Accept All` counts/operates on the **current** parse run only (stale keys excluded from "already accepted").
- Promote **blocks** stale candidates (structured 409); promote **allows** current candidates.
- Promoted-fact supersession preserves historical facts (`effective_to`/`superseded_by`).
- Draft baseline does **not** auto-update after reparse.
- Active baseline does **not** auto-update after promotion.
- O&M historical analytics remain tied to the **prior** active baseline for prior periods (period-effective selection).
- No fabricated values (NULL not 0 for `baseline_not_available`/`missing_inputs`/`pre_pto`).
- No legacy data path (no BigQuery/Firestore); SAFL never used as a baseline source.
- Reconciliation remains read-only (zero writes/commits) with the new statuses.
- Full architect review of each phase's diff.

---

## 14. Open Questions for Reviewers

These are decisions an implementation sprint should confirm before building; none block this audit:

1. **Identical-reparse policy.** For a reparse that yields a byte-identical value+evidence (fingerprint match), do we (a) silently retain acceptance with an audit note (recommended, low-friction), or (b) still force a one-click "validated" acknowledgement? §5.3 assumes (a).
2. **Schema/prompt-version sensitivity.** Should a schema/prompt-version change alone (same extracted value) count as a source-basis change requiring re-review, or only a *value/evidence* change? The fingerprint can be defined either way; default proposal includes schema/prompt in the hash (conservative).
3. **Backfill of legacy candidates.** Phase 7 proposes an audited script to populate `source_run_id`/fingerprint for existing candidates where derivable. Confirm whether legacy candidates with no recoverable run should be left fail-closed (block promotion until re-review) rather than backfilled with a guessed run.
4. **Period-effective analytics scope (G3).** Confirm appetite for the higher-risk Phase 8. If deferred, the interim honest stance is to surface a banner that historical expected reflects the *current* active baseline (not the then-active one), so the limitation is disclosed rather than silent.
5. **Reconciliation status surface area.** §8 adds eight statuses; confirm whether all are wanted or whether a smaller set (e.g., collapse `accepted_from_previous_parse` into `stale_accepted_value`) is preferred for UX simplicity.

---

## 15. Appendix — Confirmed Code Anchors

- `app/models/project_facts.py` — `ProjectFact`/`FactStatus`; lineage cols `source_file_id`, `source_run_id` (FK `ai_parsing_results`), `source_document_key_id`, `ai_extracted_value`, `effective_from/to`, `superseded_by_fact_id`; indexes `ix_project_facts_source_file`, `ix_project_facts_source_run`.
- `app/models/document.py` — `DocumentKey` unique constraint `_document_key_version_uc (document_id, file_id, name)`; **no run linkage**.
- `app/models/file.py` — `AIParsingResult` (`file_id`, `status`, `parsed_result`, `extraction_run_number`, `schema_version_id`, `prompt_template_id`, `start_time`, `end_time`); retained per run.
- `app/routers/due_diligence/files_parsing.py` — `bulk_accept_ai_values`, `allow_accept_non_latest`, `get_latest_run_for_file`, `409` on non-latest.
- `app/services/promotion_service.py` — `promote_version`, `_promote_candidate_facts` (no freshness re-check).
- `app/services/due_diligence/reconciliation_service.py` — read-only ladder + `active_baseline_outdated`.
- `app/services/telemetry/expected_service.py` / `app/helpers/telemetry/v2_chart_data.py` — compute-on-read against current active baseline.
- `app/crud/telemetry_expected.py` — baseline lifecycle (`get_active`, `approve`, `activate`, supersede; one-active partial unique index).
- Frontend: `…/DueDiligenceDocument/components/DocumentModal.tsx` (`fieldsToAccept`, `promoteStatus`, reprocess, run-history `canAcceptFromSelectedRun`), `…/Reconciliation/components/ReconciliationTable.tsx` (`StatusCell`), API clients `src/api/due-diligence.ts`, `src/api/assumptions.ts`.
