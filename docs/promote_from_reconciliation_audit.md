# Promote from Reconciliation — Audit & Design

**Status:** This document captured the original audit & design. **Phase 1 (frontend-only) has now been implemented per §10** — the Reconciliation tab can reach the existing promotion and create-task flows. No backend endpoints, migrations, schema, or task-payload changes were made; the implementation reuses the existing `promotion/diff`, `promote`, and task-tracker endpoints unchanged.
**Scope:** Project Hub → Reconciliation tab, Due Diligence (Data Room), and the existing "Promote to Current Assumptions" backend.
**Audience:** Engineering + product reviewers deciding whether/how to make promotion reachable from the Reconciliation screen.

---

## 0. Executive Summary

**Why the user "doesn't see how promotion works": there is no promotion UI anywhere in the app.**

The backend already has a complete, lender-quality promotion workflow — a `promote` endpoint, a read-only diff-preview endpoint, active/candidate fact readers, and a promotion-history audit trail. It is atomic (commits on success, rolls back on any failure) and writes an `AssumptionPromotion` audit record on every promotion.

But **nothing in the frontend reaches any of it.** A search of the frontend found zero callers of the promote, diff, facts, or promotion-history endpoints. The Data Room only performs *acceptance* (candidate-fact creation) and renders a "promoted terms" *count*; the Reconciliation tab is strictly read-only and offers only an "Open Data Room" deep link. So today, the only way to promote a value is to call the API directly. This is exactly why promotion appears not to exist.

**The single most important design constraint:** the existing promotion is **file-version-scoped and all-or-nothing**. Promoting one file version promotes *every* candidate fact attached to that file and retires every conflicting active fact for the same canonical fields. There is **no field-level promote endpoint**. A naïve row-level "Promote this field" button would therefore be dishonest — it cannot promote a single field in isolation.

**Recommendation (safe first step):** add a thin promote experience launched only from `accepted_not_promoted` Reconciliation rows that **reuses the existing diff + promote endpoints unchanged**, but always shows the complete, live-refetched file-version diff (the full blast radius) in a confirmation dialog before executing. Pair it with a broadly-available "Create Task" hand-off that reuses the existing task-tracker. Acceptance/override stays in the Data Room (DD rigor preserved); baselines stay a separate downstream step (never one-click into an active baseline). Every Reconciliation row already carries the exact `{document_id, file_id}` the promote endpoint needs, so no backend change is required for the minimum viable version.

---

## 1. Goal, Constraints & Non-Goals

### 1.1 What the user asked for
Make the "promote" step reachable from the Reconciliation screen so a reviewer can move an accepted value into the project's active assumptions without hunting for a hidden API. Support **two** paths:

1. **Promote-myself** — the current user performs the promotion now.
2. **Create-assignable-task** — the current user hands the promotion off to someone else as a tracked task.

### 1.2 Hard constraints (from the user)
- **Acceptance/override MUST stay in the Data Room.** Reconciliation may offer *only* the promote step (candidate → active fact). It must never become a second place to accept or override values — that would fork the due-diligence rigor.
- **Never drive a value into an active baseline in one click.** Promotion produces an *active fact*. Turning that into expected/O&M math is a separate, deliberate downstream action.
- **Never change the backend "Site" entity.** "Project" is UI terminology only; all backend routes and models continue to use `site_id`/`Site`.

### 1.3 Non-goals (held to in the Phase 1 implementation)
- No new endpoints, no migrations, no schema changes, no task-payload changes — Phase 1 is frontend-only and reuses existing endpoints.
- No field-level promotion was added to the backend (it does not exist today and adding it is explicitly out of scope for the first step — see §10).
- No change to acceptance, override, reconciliation, baselines, or expected math.

---

## 2. Current State — Backend Promotion (it exists and is solid)

### 2.1 Endpoints
The promotion router is mounted at `prefix="/api/projects/{site_id}/assumptions"` (`app/main.py:359`). `{site_id}` is the backend Site id; "projects" here is only a URL word, consistent with the UI-terminology rule. All routes resolve the site via `get_authorized_site` and enforce module permissions.

| Method & path | Permission | Writes? | Purpose |
|---|---|---|---|
| `GET  /api/projects/{site_id}/assumptions/facts` | `Diligence:view` | No | Active project facts (current assumptions) for downstream/UI consumption. |
| `GET  /api/projects/{site_id}/assumptions/facts/candidates/{file_id}` | `Diligence:view` | No | Candidate facts pending promotion for a specific file version. |
| `POST /api/projects/{site_id}/assumptions/promotion/diff` | `Diligence:view` | **No** | Read-only preview: what would change if this file version were promoted. Body: `{file_id}`. |
| `POST /api/projects/{site_id}/assumptions/promote` | `Diligence:edit` | **Yes** | Promote a file version to current assumptions. Body: `{document_id, file_id, notes?}`. |
| `GET  /api/projects/{site_id}/assumptions/promotions` | `Diligence:view` | No | Promotion audit trail for the site. |

### 2.2 Promotion semantics (the blast radius)
`PromotionService.promote_version(site_id, document_id, file_id, promoted_by_id, notes)` (`app/services/promotion_service.py`) does the following, **in one transaction**:

1. Validates `file → document → site` ownership (raises `FILE_NOT_FOUND`, `FILE_DOCUMENT_MISMATCH`, `DOCUMENT_SITE_MISMATCH`).
2. Computes the diff (same logic as the preview endpoint).
3. Marks all *other* file versions of the same document `is_actual = False`, and marks the promoted file `is_actual = True`.
4. For **every** candidate fact on that file (`get_candidate_facts_for_file`): retires the conflicting active fact for that canonical field (sets `retired`, `superseded_by_fact_id`, `effective_to`) and promotes the candidate to `active` (sets `promoted_by_id`, `promoted_at`, `promotion_notes`, `effective_from`).
5. Writes an `AssumptionPromotion` audit record (`site_id, document_id, file_id, promoted_by_id, notes, diff_json`).
6. `commit()`. **Any exception → `rollback()`** and a `PROMOTION_FAILED` error (mapped to HTTP 400). There is no partial promotion.

**Key takeaways for the design:**
- The unit of promotion is the **file version**, not the field. There is no `promote_field(...)`.
- Promotion **retires** conflicting active facts **only for fields that have a candidate on the promoted version** (`_promote_candidate_facts` iterates only over the new version's candidate facts) — promoting File B for a field that File A currently owns silently flips ownership of that field. The diff surfaces this as `changed` rows, which is exactly why the confirmation must show the full diff.
- The diff *also* reports `removed` entries — active facts from the *same document* whose field is **absent** from the new version — but **promotion never retires these**. Because `_promote_candidate_facts` only touches fields that have a candidate, a `removed` row is a **preview/anomaly signal** (the new version dropped a field the old one carried), **not** an actual write effect. The confirmation may show `removed` rows for transparency, but must never imply the promotion will delete them.

### 2.3 Diff shape
`compute_promotion_diff(site_id, file_id)` returns:
```jsonc
{
  "has_changes": true,
  "changes": [
    { "type": "added"|"changed"|"removed",
      "field_name": "Module Wattage", "field_id": 12,
      "current_value": "...", "new_value": "...",
      "current_source_file_id": 41, "new_source_file_id": 42 }
  ],
  "summary": { "added": 1, "changed": 2, "removed": 0 }
}
```
This is the authoritative preview payload and should drive the confirmation dialog. **Caveat:** `added`/`changed` rows correspond to real write effects (a candidate is promoted; the conflicting active fact is retired), but `removed` rows do **not** — see §2.2. The dialog must present `removed` as informational ("this version no longer carries these fields"), never as a deletion the promotion performs.

### 2.4 What promotion does NOT touch
Promotion writes only `files.is_actual`, `project_facts`, and `assumptions_promotions`. It does **not** create, modify, or activate any baseline, design point, or O&M/expected math. Reaching a baseline is a separate bridge (see §9).

---

## 3. Current State — Frontend (no promotion path exists)

- **Reconciliation tab** (`.../tabs/Reconciliation/`): strictly read-only. `ReconciliationTable.tsx` renders a status chip, a single most-severe blocking chip, a "Next: …" required-action caption, missing-dependency chips, and — for a gated subset of statuses — an "Open Data Room" deep link. It has **no** promote control and never calls the assumptions endpoints.
- **Data Room** (`.../tabs/DataRoom/`): performs acceptance/override and shows a "promoted terms" count, but does not call `promote`/`promotion/diff` either. The "promoted" count is a read of fact status, not a promotion action.
- **API client**: there is no generated/typed client method for the promote/diff/facts/promotions endpoints in use.

**Conclusion:** the gap is entirely on the frontend. The backend is ready; the app simply never surfaces it.

---

## 4. The Reconciliation Row as the Launch Point

Each Reconciliation row (`app/schema/reconciliation.py::ReconciliationRow`) already carries everything the promote and task flows need. No backend change is required to launch promotion from a row.

### 4.1 Provenance / navigation handles on every row
- `canonical_field`, `display_label`, `category`, `baseline_target`
- `status` + presentation fields: `status_label`, `status_explanation`, `required_action`, `blocking_level`, `missing_dependencies[]`
- Value chain: `ai_extracted_value`, `accepted_value`, `active_fact_value`, `draft_baseline_value`, `active_baseline_value`, `legacy_value`
- Provenance IDs: `project_fact_id` (= `fact_id`), `source_file_id`, `source_run_id` (= `ai_run_id`), `document_id`, `document_version_id` (the source File id), `document_key_id`, `baseline_id`, `baseline_point_id`
- Context: `candidate_count`, `aliases_matched[]`, `required_for_baseline`, `supersedes_fact_id`, `warnings[]`, `confidence`, `evidence_page`, `evidence_snippet`

### 4.2 The two inputs the promote endpoint needs
The promote endpoint needs `{document_id, file_id}`. On an `accepted_not_promoted` row these map directly to:
- `document_id` ← `row.document_id`
- `file_id` ← `row.document_version_id` (the source File / document version)

Because promotion is file-version-scoped, the row's `source_file_id`/`document_version_id` identifies the version whose *entire* accepted set will be promoted — which is why the confirmation must re-fetch and display the full diff for that version rather than implying single-field scope.

---

## 5. Status → Action Map (where "Promote" may appear)

The reconciliation service already computes the precise lifecycle stage per field and a `required_action` string. The promote affordance must only appear where promotion is the genuine next step.

| Status | Meaning | Backend `required_action` | Promote button? | Why |
|---|---|---|---|---|
| `missing` | No value anywhere | "Extract/enter, then accept and promote" (if required) | No | Nothing to promote; action is in Data Room. |
| `ai_extracted_only` | AI value, unreviewed | "Accept in Due Diligence, then promote" | No | Must be accepted first (Data Room). |
| `accepted_document_value` | Accepted key, no fact | "Re-accept so a fact is created, then promote" | No | Anomaly; fact must exist first (Data Room). |
| `candidate_only` | Candidate, not accepted | "Accept in Due Diligence, then promote" | No | Acceptance precedes promotion (Data Room). |
| **`accepted_not_promoted`** | **Accepted/overridden, not promoted** | **"Promote this accepted value to the project's active assumptions."** | **YES** | This is exactly the promote step. |
| `active_fact` | Promoted, not on a baseline | "Create/activate a baseline…" (if driving) | No | Already promoted; next step is baseline. |
| `in_draft_baseline` | On a draft baseline | "Activate the draft baseline…" | No | Already promoted. |
| `in_active_baseline` | On active baseline | none / "Rebuild if outdated" | No | Already live. |
| `superseded` | Only retired remains | "Accept and promote a current value…" | No | Needs a fresh accepted value first (Data Room). |

**Rule:** the **Promote** control is shown **only** for `accepted_not_promoted`. Every other "needs human work" status routes to the Data Room (its `status` is in the existing `ACTIONS_IN_DATA_ROOM` set: `{missing, ai_extracted_only, accepted_document_value, candidate_only, accepted_not_promoted, superseded}`), preserving the "acceptance stays in Data Room" constraint. Note `accepted_not_promoted` is currently in that Data-Room set; the design adds an *additional* in-place Promote action for it rather than removing its Data Room link.

---

## 6. Design — Promote-Myself Flow

### 6.1 Entry point
On `accepted_not_promoted` rows only, render a **Promote** button next to the "Next: …" caption. Gate it on the caller holding `Diligence:edit` for the site (the same permission the endpoint enforces). Users with only `Diligence:view` see the row and its status but not the button (they may still use Create Task — see §7).

### 6.2 Mandatory confirmation with full, live diff
Clicking **Promote** must:

1. Call `POST /api/projects/{site_id}/assumptions/promotion/diff` with `{file_id: row.document_version_id}` **at click time** (never reuse a stale diff) to get the current blast radius.
2. Render a confirmation dialog that makes the file-version scope explicit:
   - A header that names the **document + version** being promoted, and states plainly: *"Promoting this version will update every accepted value on it, not just this field."*
   - The full `changes[]` table grouped by `added` / `changed` / `removed`. `added`/`changed` are real effects; label `removed` as informational ("the new version no longer carries this field") because promotion does not retire those — see §2.2. Highlight the row the user launched from.
   - The `summary` counts (added/changed/removed).
   - An optional **notes** field (persisted to `promotion_notes` + the audit record).
   - Confirm / Cancel.
3. On confirm, call `POST /api/projects/{site_id}/assumptions/promote` with `{document_id: row.document_id, file_id: row.document_version_id, notes}`.
4. On success, invalidate the reconciliation query (and facts/promotions queries) so the row transitions to `active_fact`. Surface the `facts_promoted` count and a link to the promotion history.

### 6.3 Honesty requirements
- The dialog must **never** claim "promote only this field." Because the endpoint is all-or-nothing, the UI must disclose the complete diff.
- If `has_changes` is `false` (e.g., the version's facts already match active), show a no-op explanation and disable confirm.
- If the diff returned at confirm-time differs from what launched the dialog (a race), re-render with the fresh diff and require re-confirmation.
- `removed` entries are not deletions the promotion performs; never present them as data that will be erased.

### 6.4 Error handling
Map the backend `PromotionError` codes to clear messages: `FILE_NOT_FOUND`, `FILE_DOCUMENT_MISMATCH`, `DOCUMENT_SITE_MISMATCH` → "This version is no longer valid for promotion; refresh and try again." `PROMOTION_FAILED` → "Promotion failed and nothing was changed." (the backend already rolled back).

---

## 7. Design — Create-Assignable-Task Flow

For reviewers who cannot or should not promote themselves (or want a second person to do it), offer **Create Task**. This reuses the existing task-tracker; no new task infrastructure is needed.

### 7.1 Availability
Create Task can be offered more broadly than Promote — on any row whose `required_action` is non-null (i.e., there is a real next step), not just `accepted_not_promoted`. The task simply records "do this next step." Creating a task requires `Diligence:edit` (the task-create endpoint is `Diligence`-gated).

### 7.2 API shape (existing task-tracker)
1. **Resolve the board** for the site's Diligence module: `GET /api/task-tracker/boards/?entity_type=site&entity_id={site_id}&module=Diligence`.
2. **Look up assignees**: `GET /api/task-tracker/boards/{board_id}/assignees?search=`.
3. **Create the task**: `POST /api/task-tracker/boards/{board_id}/tasks/` with the fields `TaskCreationPayloadSchema` (`app/schema/task.py`) actually accepts: `{name, priority, due_date (required), status_id, assignee_id?, affected_device_id?, alert_id?, description?}`. **There is no `document_id` field on the create payload** — the only optional FK links are `affected_device_id` and `alert_id`, neither of which applies here. Document-level boards additionally reject task creation (HTTP 400, "Task adding to the Document level boards is prohibited"). So a created task **cannot be structurally linked to the source document today.**

### 7.3 Prefill from the row
- `name`: e.g. *"Promote '{display_label}' to current assumptions"*.
- `description`: encode the field + **all** provenance, because the create payload exposes **no structural link** to a document, canonical field, or reconciliation row. Include `display_label`/`canonical_field`, current `status`, the `required_action`, and the IDs (`project_fact_id`, `source_file_id`/`document_version_id`, `document_id`, `document_key_id`, `ai_run_id`). This is the ONLY way to carry the reference, so the assignee can reconstruct the exact row.
- `due_date`: required by the endpoint — default to a sensible horizon (e.g., +7 days) and let the user edit.
- `priority`/`status_id`/`assignee_id`: surfaced in the dialog; `assignee_id` from the assignee picker.
- Do **not** attempt to link `affected_device_id`/`alert_id` (not relevant here).

### 7.4 Limitation to call out
The task create payload supports **no structural link at all** for this use case (no `document_id`; `affected_device_id`/`alert_id` are irrelevant), so the field/document/row reference must live entirely in free-text `description`. If precise machine-linkage to a document, canonical field, or reconciliation row is later required, that needs a backend change (expose/add a nullable FK on `TaskCreationPayloadSchema`) — out of scope for the first step.

---

## 8. Permission Model

| Action | Required permission | Source of truth |
|---|---|---|
| View Reconciliation | `Diligence:view` | reconciliation endpoint guard |
| View facts / diff / promotion history | `Diligence:view` | assumptions router guards |
| **Promote (write)** | **`Diligence:edit`** | `POST /promote` guard |
| Create task | `Diligence:edit` | task-create guard |
| Accept / override (Data Room) | `Diligence:edit` | DD endpoints (unchanged) |

**Discrepancy to flag (documentation only):** the promote endpoint's docstring and `description` say *"Role-gated: Company Admin or System User only"*, but the actual enforcement is `require_module_permission(..., module_key="Diligence", action="edit")`. The effective gate is **Diligence:edit**, not a Company-Admin role check. The behavior is correct and intentional for module-level enforcement; the **docstring is stale and should be corrected** in a future change so reviewers are not misled. (No code change made here.)

---

## 9. Relationship to Baselines (the "never one-click to active" boundary)

Promotion ends at an **active project fact**. It deliberately stops short of any baseline. Reaching expected/O&M math is a separate, multi-step, opt-in bridge:

1. **Promote** → active fact (this design).
2. **Create draft baseline from facts**: `POST /api/telemetry/v2/sites/{site_id}/expected-baseline/create-draft-from-facts` (requires `telemetry_admin` + company-admin; returns `422 review_required` when inputs are insufficient; idempotent; produces a **draft** only and never auto-activates; never reads SAFL).
3. **Activate** the draft (a further separate, deliberate action).

The Reconciliation UI may *inform* the user of these next stages (it already does, via `required_action` like "Create and activate a baseline…" and the `missing_dependencies` chips), but the Promote action must **not** chain into baseline creation or activation. This satisfies "never drive a value into an active baseline in one click."

---

## 10. Recommended Implementation Scope & Sequencing

### Phase 1 — Minimum viable, no backend change (IMPLEMENTED)
- Frontend-only. Reuse `promotion/diff` + `promote` exactly as they exist.
- Add the **Promote** button to `accepted_not_promoted` rows, gated on `Diligence:edit`.
- Add the **full-diff confirmation dialog** (live-refetched, blast-radius honest, optional notes).
- Add **Create Task** (prefilled, free-text provenance only — no structural document link is available) on actionable rows.
- Add a typed API client for the assumptions + task-tracker calls.
- Invalidate reconciliation/facts/promotions queries on success.

This delivers both requested paths (promote-myself + create-task) without touching the backend, and is fully honest about the file-version blast radius.

### Phase 2 — Optional backend enhancements (only if product wants them)
- **Field-scoped promotion** (a real `promote_field` path) so a row-level button can promote exactly one field. This is a genuine backend feature (new service method + endpoint + audit semantics) and changes the "all-or-nothing" contract — it must be designed deliberately, not implied by the UI.
- **Structured task linkage** to a canonical field / reconciliation row (new nullable column on tasks) so hand-offs are machine-linkable rather than free-text.
- **Docstring correction** on the promote endpoint to state the true `Diligence:edit` gate.

### Explicitly deferred / not recommended now
- Any in-Reconciliation acceptance/override (violates the Data Room constraint).
- Any one-click promote→baseline chaining (violates the baseline boundary).

---

## 11. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | UI implies single-field promote but endpoint is all-or-nothing → unexpected mass changes. | High if unmitigated | High | Mandatory full-diff confirmation; explicit "this version updates every accepted value" copy; launch only from `accepted_not_promoted`. |
| R2 | Stale diff between dialog open and confirm → user approves the wrong blast radius. | Medium | High | Re-fetch diff at confirm-time; re-confirm if it changed. |
| R3 | Reviewers conflate Promote with Accept and start "accepting" in Reconciliation. | Medium | Medium | No accept/override controls in Reconciliation; non-promote statuses route to Data Room only. |
| R4 | Users expect promotion to update expected/O&M output immediately. | Medium | Medium | Post-promote messaging states the value is now an active fact; baseline creation/activation is separate (§9). |
| R5 | Permission confusion from the stale "Company Admin only" docstring. | Low | Low | Document the true `Diligence:edit` gate (§8); recommend docstring fix in Phase 2. |
| R6 | Task hand-off loses the field reference (the create payload exposes no document/field FK at all). | Medium | Low | Encode full provenance in `description`; flag structured linkage as Phase 2. |
| R7 | Promote silently retires another file's active fact for the same field. | Medium | Medium | Diff surfaces `changed` rows; confirmation shows them prominently. |
| R8 | UI presents diff `removed` rows as deletions, implying promotion will erase fields it never touches. | Medium | Medium | Label `removed` as informational only (§2.2/§2.3); `added`/`changed` are the only real write effects. |

---

## 12. Discrepancies & Findings Log (for the record)

1. **No frontend promotion path exists** — backend is complete and unreachable from the app. (Root cause of "I don't see how promotion works.")
2. **Promotion is file-version-scoped and all-or-nothing** — no field-level endpoint; promoting a version promotes all its candidate facts and retires conflicting active facts.
3. **Promote endpoint docstring is stale** — says "Company Admin or System User only" but enforces `Diligence:edit`.
4. **Diff is authoritative and read-only** — the preview endpoint and the in-promotion diff share `compute_promotion_diff`, so the confirmation can trust the preview.
5. **Task linkage has no usable FK for this case** — `TaskCreationPayloadSchema` exposes only `affected_device_id`/`alert_id` (no `document_id`, and neither applies); document-level boards reject task creation. All provenance must live in free-text for now.
6. **Reconciliation already computes the right "next step"** — `required_action` + `status` + `ACTIONS_IN_DATA_ROOM` give the exact gating needed to place a Promote affordance without new backend logic.
7. **Diff `removed` rows are not write effects** — `compute_promotion_diff` reports active facts whose field is absent from the new version as `removed`, but `_promote_candidate_facts` never retires them. They are preview/anomaly signals only; the UI must not present them as deletions.

---

## 13. Open Questions / Decisions Needed

1. **Field-scoped promotion:** is Phase-1's honest "promote the whole version (with full diff)" acceptable, or does product require true single-field promotion (Phase 2 backend work)?
2. **Create Task breadth:** offer Create Task on *all* actionable rows, or only on promote-relevant (`accepted_not_promoted`) rows?
3. **Default task due-date horizon:** the endpoint requires `due_date` — what default (e.g., +7 days)?
4. **Notes requirement:** should promotion notes be mandatory for baseline-driving fields (mirroring the override-rationale guardrail), or always optional?
5. **Post-promote guidance:** should the success state actively guide the user toward the baseline bridge (link), or stay informational only?

---

## 14. Appendix — Exact References

**Promotion backend**
- Service: `app/services/promotion_service.py` (`promote_version`, `compute_promotion_diff`, `_promote_candidate_facts`).
- Router: `app/routers/project_assumptions.py` (mounted `prefix="/api/projects/{site_id}/assumptions"`, `app/main.py:359`).
- CRUD: `app/crud/project_fact.py` (`get_candidate_facts_for_file`, `retire_active_fact`, `promote_candidate_to_active`), `app/crud/assumption_promotion.py`.
- Models: `app/models/project_facts.py` (`ProjectFact`, `FactStatus`, `AssumptionPromotion`).
- Facts service: `app/services/project_facts_service.py`.

**Reconciliation (launch source, read-only)**
- Service: `app/services/due_diligence/reconciliation_service.py` (`build_site_reconciliation`, `_required_action`, `_blocking_level`).
- Router: `app/routers/due_diligence/reconciliation.py` (`GET /api/due-diligence/sites/{site_id}/reconciliation`, mounted `app/main.py:348`).
- Schema: `app/schema/reconciliation.py` (`ReconciliationRow` and its provenance/nav fields).
- Catalog: `app/static/reconciliation_catalog.py`.
- Frontend: `.../tabs/Reconciliation/components/ReconciliationTable.tsx`, `.../Reconciliation/utils.ts` (`ACTIONS_IN_DATA_ROOM`, status/blocking metadata), `StatusChip.tsx`, `WarningChips.tsx`.

**Baseline bridge (separate, downstream — not chained)**
- `POST /api/telemetry/v2/sites/{site_id}/expected-baseline/create-draft-from-facts` (`app/routers/telemetry/v2.py`), `app/services/telemetry/baseline_from_facts_service.py`.

**Task hand-off (existing task-tracker)**
- Boards: `GET /api/task-tracker/boards/?entity_type=site&entity_id={site_id}&module=Diligence`.
- Assignees: `GET /api/task-tracker/boards/{board_id}/assignees?search=`.
- Create: `POST /api/task-tracker/boards/{board_id}/tasks/` (`app/routers/task_tracker/tasks.py`); payload schema `app/schema/task.py::TaskCreationPayloadSchema` (no `document_id`; document-level boards rejected with HTTP 400).
- Frontend client: `src/api/task-management.ts`.
