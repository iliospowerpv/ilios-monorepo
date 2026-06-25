# Baseline Review, Approval, Activation, and Staleness UX — Audit & Implementation Plan

**Status:** Planning / audit sprint. **No production code was changed.** This document is the deliverable.
**Date:** 2026-06-25
**Scope owner:** Telemetry / Expected-Baseline governance
**Constraint reminder:** no baseline math/formula changes; no automatic draft/approve/activate/supersede/deactivate; no historical expected rewrite; no BigQuery/Firestore/SAFL/legacy as operational truth; no weather-semantic inference; no WS.5 work.

---

## 0. Scope, method, and key corrections to prior assumptions

### 0.1 What this audit covers
The governed lifecycle of the **weather-adjusted expected baseline** (the operational "expected" line) and, where it intersects, the **design-estimate** baseline (12 monthly + annual points). It traces the backend lifecycle, the frontend surfaces, permissions, audit trail, validation, period-effective selection, and staleness/source-basis handling, then proposes one coherent Baseline Management UX and an implementation/test plan.

### 0.2 Method
- Read the live model, enums, CRUD, services, routers, and frontend components (read-only).
- Verified the DB schema and **Site 4's actual baseline rows** directly against PostgreSQL.
- Cross-checked three independent code traces (backend lifecycle, frontend surfaces, safety/permissions) and resolved their disagreements against first-hand schema + router inspection.

### 0.3 Corrections to earlier internal notes (important — read first)
Prior internal notes are **partly stale**. This audit supersedes them on three points:

1. **A reviewer-facing approve/activate/compare UI already exists.** Earlier notes said "there is no frontend to review / preview / approve / activate a draft." That is no longer true. `DraftBaselineReviewPanel.tsx` already calls `approveExpectedBaseline`, `activateExpectedBaseline`, `getBaselineDiff`, and `getActiveExpectedBaseline`; `BaselineFromFactsPanel.tsx` creates drafts; `ReadinessSummary.tsx` shows readiness. The remaining gaps are **narrower and more specific** than "no UI" (see §A and §B).

2. **Activation attribution is NOT a first-class column.** There is no `activated_by` / `activated_at` column on `telemetry_expected_baselines`. Activation identity/time are stamped **inside `validation_result_json`** (`activated_by_user_id`, `activated_at`) by `TelemetryExpectedBaselineCRUD.activate`. (The `activated_by`/`activated_at` columns that exist belong to the **weather** module's `weather_device_mappings`, a different governance surface.) This is an attribution/queryability gap, not a present column.

3. **Approve/activate require company-admin in addition to telemetry-admin.** The route decorators carry `Depends(telemetry_admin_required)` **and** the handler resolves the site through `get_authorized_site_with_company_admin(...)`. So the true backend gate for create/approve/activate/diff is **telemetry-admin AND company-admin-on-site**. The frontend gate (`useTelemetryAdminPermission`) only checks telemetry-admin, so a telemetry-admin-without-company-admin user passes the FE gate and then gets a 403. This asymmetry is a live defect (see §D).

---

## A. Current-state audit

### A.1 Data model & enums (verified against PostgreSQL)

**Tables:** `telemetry_expected_baselines` (versioned header) + `telemetry_expected_baseline_points` (stored points; used only by `design_estimate`).
**Model file:** `backend/ilios-server/app/models/telemetry_expected.py`.

**Status enum (`telemetry_baseline_status_enum`):** `draft`, `in_review`, `approved`, `active`, `superseded`, `rejected`.
**Type/methodology enum (`telemetry_baseline_type_enum`):** `design_estimate`, `weather_adjusted_model`, `imported_8760`, `manual`.
**Source enum (`telemetry_baseline_source_enum`):** `pvsyst`, `design_document`, `diligence_ai_parse`, `manual_entry`, `imported_8760`, `legacy_formula`.

**Header columns that matter for lifecycle/governance:**
- Identity/version: `id`, `company_id`, `site_id`, `baseline_name`, `baseline_type`, `status`, `version`.
- Effective dating: `active_from`, `active_to` (naive-UTC).
- Supersession: `supersedes_baseline_id` (self-referential chain).
- Attribution: `created_by_user_id`, `reviewed_by`/`reviewed_at`, `approved_by`/`approved_at`. **No `activated_by`/`activated_at` columns** — activation identity lives in `validation_result_json`.
- Provenance: `source_type`, `source_document_id`, `source_project_fact_id`, `ai_confidence_json`, `model_parameters_json` (carries `field_sources`, `design_points` metadata, etc.).
- Validation: `validation_result_json`, `validation_policy_version`.
- Physics snapshot (immutable once activated): `module_wattage`, `module_quantity`, `inverter_wattage`, `inverter_quantity`, `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct`, `soiling_factor`, `dc_loss_pct`, `ac_loss_pct`, `medium_voltage_loss_pct`, `mv_line_loss_pct`, `pto_date`, `timezone`, `system_size_ac_kw`, `system_size_dc_kw`, `degradation_rate`.
- Loss detail: `loss_assumptions_json`.

**Points columns (`telemetry_expected_baseline_points`):** `baseline_id`, `site_id`, `device_id`, `point_ts`, `interval_minutes`, `expected_power_kw`, `expected_energy_kwh`, `irradiance_wm2`, `cell_temperature_f`, `ambient_temperature_f`, `source_granularity` (enum), `calculation_method`. **Weather-adjusted baselines store ZERO points** (they compute on read); points exist only for `design_estimate`.

**Single-active invariant:** partial unique index `WHERE status='active'` per (site, baseline_type) + `FOR UPDATE` supersede in the activate transaction. A true concurrent-activation race surfaces as an IntegrityError 500 (accepted, not a clean 409).

### A.2 Current-state endpoint / UI capability matrix

Full backend prefix is `/api/telemetry/v2`. Permission column shows the **real** gate (route dependency + site resolver).

| Capability | Endpoint (method + path) | Service / CRUD | Permission (true gate) | UI surface | Verdict |
|---|---|---|---|---|---|
| List baselines | `GET /sites/{site_id}/expected-baselines` | `crud.list_*` | `get_authorized_site` (view) | `DraftBaselineReviewPanel` (history section) | Visible |
| Get active baseline | `GET /sites/{site_id}/expected-baselines/active` | `crud.get_active` | `get_authorized_site` (view) | `DraftBaselineReviewPanel` (status summary) | Visible |
| Readiness (from facts) | `GET /sites/{site_id}/expected-baseline/readiness-from-facts` | `baseline_from_facts_service.evaluate_readiness` | `telemetry_admin_required` | `BaselineFromFactsPanel`, `ReadinessSummary` | Visible |
| Create draft (from facts) | `POST /sites/{site_id}/expected-baseline/create-draft-from-facts` | `baseline_from_facts_service.create_draft_from_facts` | telemetry-admin **AND** company-admin | `BaselineFromFactsPanel` | Visible |
| Create draft (legacy SAFL) | `POST /sites/{site_id}/expected-baselines` (**deprecated**) | `crud.create_draft` | telemetry-admin **AND** company-admin | none (backfill only) | Hidden / deprecated |
| Design points readiness | `GET /expected-baselines/{baseline_id}/points-readiness` | `baseline_points_service` | telemetry-admin | partial (`ReadinessSummary` design-estimate) | Incomplete |
| Generate design points | `POST /expected-baselines/{baseline_id}/generate-design-points` | `baseline_points_service` | telemetry-admin | none | Hidden |
| Replacement diff (compare) | `GET /expected-baselines/{baseline_id}/diff` | `_build_baseline_diff` | telemetry-admin **AND** company-admin | `DraftBaselineReviewPanel` (field-diff table) | Incomplete (table only, no curve overlay) |
| Approve | `POST /expected-baselines/{baseline_id}/approve` | `crud.approve` | telemetry-admin **AND** company-admin | `DraftBaselineReviewPanel` (Approve action) | Visible; **no separation-of-duties** |
| Activate | `POST /expected-baselines/{baseline_id}/activate` | `crud.activate` | telemetry-admin **AND** company-admin | `DraftBaselineReviewPanel` (Activate action) | Visible; **no explicit effective-date control** |
| Expected preview (curve) | `GET /sites/{site_id}/expected-preview` | `expected_service.compute_site_expected` | `get_authorized_site` (view) | O&M `ActualProjectedPower` | **Refuses `draft`** (previewable = approved/active/superseded) |
| Period-effective expected (O&M) | O&M actual-vs-expected read path | `expected_service.compute_site_expected` → `crud.get_baselines_effective_in_window` | `get_authorized_site` (view) | `ActualProjectedPower` chart | Visible |
| Invalid-baseline read behavior | (read path, all expected reads) | `baseline_physics_validation.validate_baseline` | n/a (read) | `BaselineInvalidBanner` | Visible; validate-on-read suppression |
| Reconciliation (fact↔baseline audit) | `GET` reconciliation endpoint | `reconciliation_service.build_site_reconciliation` | `Diligence:view` | `Reconciliation.tsx`, `ReconciliationTable` | Visible (read-time) |
| Promote facts (source basis) | `POST` promote-version | `promotion_service.promote_version` + freshness guard | `Diligence:edit` (company-admin) | promote-from-reconciliation UI | Visible |
| Supersede (standalone) | — none — | (only implicit inside `activate`) | — | none | **Missing** |
| Deactivate (no replacement) | — none — | — | — | none | **Missing** |
| Active-baseline staleness flag | — none for physics/fact baselines — | reconciliation read-time `W_ACTIVE_OUTDATED` only | `Diligence:view` | reconciliation warning chips | **Incomplete / not proactive** |
| Activation audit event row | — none (JSONB only) — | `validation_result_json` | — | not surfaced | **Missing as queryable event** |
| Acknowledge validation warning | (param) `acknowledge_warnings=true` + `activation_source_note` on activate | `crud.activate` | telemetry-admin **AND** company-admin | `DraftBaselineReviewPanel` (warning-ack flow) | Visible |

### A.3 Capability-by-capability detail

For each: **service/endpoint → request/response → permission → UI → verdict → mutation → expected/O&M impact → gap.**

**1. Draft creation**
- *From facts (canonical V2):* `POST /sites/{site_id}/expected-baseline/create-draft-from-facts`. Request: reviewer-supplied datasheet constants (`thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct`) + optional normalization confirmations (each requires BOTH `source_fact_id` AND `raw_value`). Response: created draft or structured 422 `review_required` with honest `missing_fields` (returned as a 422 **body**, never a raised HTTPException). Reads only promoted/active `project_facts` for module/inverter physics; never touches SAFL; never fabricates defaults. Mutation: inserts `status=draft` only; never approves/activates; existing active untouched; idempotency scoped to `status=draft`. Provenance: `source_type=diligence_ai_parse`, `source_project_fact_id` (module_wattage fact), per-field `field_sources`, content signature; `source_document_id` set only when exactly one contributing doc resolves. **Gap:** the 5 datasheet constants have no fact source and no reconciliation row — they are reviewer-supplied-only and invisible to the audit/reconciliation ladder.
- *Legacy SAFL snapshot:* `POST /sites/{site_id}/expected-baselines` — **deprecated** (returns 201 + logs a warning steering to create-draft-from-facts). Retained for manual/backfill; SAFL is **not** a V2 baseline source.

**2. Baseline preview**
- `GET /sites/{site_id}/expected-preview` → `expected_service.compute_site_expected`. Permissioned at **view** level (`get_authorized_site`) so any O&M viewer can see it. `_PREVIEWABLE_BASELINE_STATUSES` = {approved, active, superseded}. **Verdict / gap (high):** a `draft` cannot be previewed. A reviewer therefore approves a draft **without ever seeing its expected curve** — only the readiness panel and the field-diff table. This is the single biggest decision-support hole.

**3. Validation**
- Module: `baseline_physics_validation.validate_baseline` (pure, no writes). Verdicts: `hard_invalid` (blocking) vs `warning` vs ok.
- *Activation write path:* `crud.activate` calls `validate_baseline(..., validation_source_mode="activation_gate")` BEFORE supersede/commit. `hard_invalid` blocks outright via structured **409 JSONResponse** (must not be a plain HTTPException — the global handler `str()`s `detail`). On block, both the draft and the existing active row are left untouched (fail-closed).
- *Read path (validate-on-read):* every expected read validates the **owning** baseline per segment. Blocking → per-bucket `baseline_invalid`: expected suppressed to null (**never a fabricated 0**); actual + weather preserved verbatim; owning `baseline_id` stamped; provenance exposed additively as `invalid_baseline_segments`. The invalid row is **never mutated** and history is **never recomputed**.
- *Replacement diff:* `validate_baseline(..., validation_source_mode="replacement_diff")` validates both sides.

**4. Warnings & acknowledgement**
- A `warning`-only baseline can be activated **only** with `acknowledge_warnings=true` AND a non-empty `activation_source_note` (≤2000 chars). Both are stamped into `validation_result_json`. **Gap:** warnings are currently summarized in the activate dialog but the exact physics rule / affected field / expected impact is not consistently surfaced field-by-field before the reviewer acknowledges (risk of "blind acknowledgement").

**5. Approval**
- `POST /expected-baselines/{baseline_id}/approve` → `crud.approve`: stamps `reviewed_by`/`reviewed_at` (if null) + `approved_by`/`approved_at`, status → `approved`. **Gaps:** (a) no separation-of-duties (approver may equal creator); (b) optional approval note is not a first-class persisted field (notes column is generic); (c) `in_review`/`rejected` statuses exist in the enum but **no endpoint transitions into them** — there is no reject path and no explicit "submit for review" step.

**6. Activation**
- `POST /expected-baselines/{baseline_id}/activate` → `crud.activate`. Effective-from logic: **first** activation of a `weather_adjusted_model` with a `pto_date` and no prior active row → `active_from` backdated to PTO (date→naive-UTC midnight) so the post-PTO O&M window is covered; a **replacement** activation uses `now` and closes the prior row at `active_to=now`. Supersede: locks the prior active row `FOR UPDATE`, sets it `superseded` + `active_to=now`; new row `active`, `active_from`, `supersedes_baseline_id` = prior id. **Gaps:** (a) effective date is server-decided — the reviewer cannot choose an explicit effective date/time; (b) activation identity is JSONB-only (`validation_result_json.activated_by_user_id`), not a queryable column or a discrete audit event.

**7. Effective dates**
- `active_from`/`active_to` form a half-open interval. Selection: `crud.get_baselines_effective_in_window(site_id, start, end)` = `active_from <= end AND (active_to IS NULL OR active_to > start)`. This is the only correct read for "which baseline owns this bucket."

**8. Supersession**
- Only ever happens **implicitly inside `activate`**. There is **no standalone supersede** and **no deactivate-without-replacement**. So an operator who realizes the active baseline is wrong but has no replacement ready cannot cleanly retire it; their only lever is the validate-on-read suppression (which requires the baseline to be physically invalid, not merely stale).

**9. Invalid baseline behavior**
- State `baseline_invalid` from `ExpectedState`. Per-segment suppression means even a **superseded** invalid segment inside the read window emits null (not garbage). Company active-only path (zero invalid segments) is unchanged. **Verdict:** safe and honest; this is the mechanism that contained Site 4's thermal=350 incident.

**10. Period-effective selection**
- See (7). The O&M chart stitches segments; each bucket is driven by the baseline active at its `bucket_start`; ownership dedupe at boundaries via `_effective_baseline_at`. **Verdict:** correct; this is what prevents a new activation from silently rewriting history.

**11. Source freshness / stale basis**
- *At promotion time only:* `promotion_service.validate_promotion_freshness` blocks promoting a candidate fact whose `source_run_id` is older than the file version's latest completed parse run (baseline-driving fields are stricter: lineage, not value-match, is the gate). Structured **409** with top-level `error_code: PROMOTION_SOURCE_STALE`.
- *For an already-active baseline:* there is **no proactive stale guard** for physics/fact baselines. The reconciliation read (`W_ACTIVE_OUTDATED`) flags, at view time, that active facts changed since the baseline was created — but the active baseline stays active and nothing notifies the reviewer. (Contrast: the **weather** module has a monotonic `needs_re_review` flag driven by `upstream_change_detector` fingerprints — a pattern worth mirroring.)

**12. O&M expected-state display**
- `ActualProjectedPower` renders actual-vs-expected; `BaselineInvalidBanner` appears when the active baseline fails read-time validation; honest "unavailable" semantics throughout (null/N/A never rendered as 0). **Gap:** the chart shows only the **active** baseline; there is no draft overlay and no "what the proposed baseline would produce" preview.

**13. Data Room / DD fact linkage**
- DD accept/override writes `project_facts` candidates only (the DD→BigQuery characteristics write was removed). Facts → draft baseline via create-draft-from-facts. `Reconciliation.tsx` shows the full ladder (AI-extracted → accepted → candidate → active fact → draft/active baseline). **Gap:** the linkage is visible in Reconciliation but not surfaced inside the baseline review panel as "this field traces to document X version Y."

**14. Permissions** — see §D. **Live defect:** FE gate omits company-admin while BE requires it.

**15. Audit trail**
- Fact promotion: `AssumptionPromotion` (`promoted_by_id`, `promoted_at`, `notes`, `diff_json`). Baseline lifecycle: columns on the header (`created_by_user_id`, `reviewed_by/at`, `approved_by/at`) + `validation_result_json` (activation identity, `acknowledged_warnings`, `activation_source_note`, physics verdict snapshot). Weather: `weather_source_approvals` (append-only declare/activate/supersede/needs_re_review with rationale). **Gaps:** (a) no discrete, queryable **baseline event log** (every lifecycle transition as a row) — activation/supersession history is reconstructed from columns + JSONB; (b) no source-basis **snapshot** stored at approval/activation for later "did the basis change?" comparison of physics/fact baselines (only weather has fingerprints).

---

## B. Proposed UX workflow

One coherent **Baseline Management** experience, reachable from Project Hub → O&M / Performance Context, Project Hub → Reconciliation (its current home), and the Data Room evidence context (deep link). It is an **additive consolidation** of the panels that already exist (`DraftBaselineReviewPanel`, `BaselineFromFactsPanel`, `ReadinessSummary`, `ReconciliationTable`) plus the missing views below. No backend math changes; the only new backend work is read-only/audit endpoints called out per view.

### B.1 Screen & workflow map

```
Baseline Management (Reconciliation tab + O&M deep links)
├── 1. Baseline Status Summary ........ active id/version, lifecycle state, effective window,
│                                        coverage, source-basis status, physics status,
│                                        last reviewer/action, O&M impact line
├── 2. Draft Baseline Review .......... full source-backed field table (raw→normalized→unit→
│                                        evidence→confidence→source doc/version→override→driving)
├── 3. Physics Validation & Warnings .. blocking errors + warnings, each with rule, field,
│                                        expected impact, required action, ack requirement
├── 4. Approval ....................... permission + non-blocking validation + explicit action +
│                                        optional note + recorded identity/time/version
├── 5. Activation ..................... approved-only + explicit effective date/time +
│                                        downstream-impact confirmation + period-effective preview
├── 6. Preview / Compare .............. active vs proposed: changed inputs + expected curve overlay +
│                                        effective-date boundary + impacted/unavailable periods
├── 7. Staleness / Source-Basis Review  "active baseline source basis changed" + exact changed
│                                        fact/doc + usable/stale/invalid + required action + links
└── 8. History & Audit Trail .......... draft→approval→activation→supersession→ack→stale events,
                                         effective dates, reviewer identities, basis snapshot, evidence
```

### B.2 The eight views

**View 1 — Baseline status summary.** Shows active baseline id/version; lifecycle state (taxonomy §C.1); `effective_from`/`effective_to`; expected-coverage state (`available`/`partial`/`missing_inputs`/`pre_pto`/`baseline_invalid`/`baseline_not_available`); source-basis status (fresh/changed/unknown); physics-validation status; last reviewer + action + time; and a one-line O&M impact statement ("Active baseline drives the expected line in the O&M actual-vs-expected chart for buckets on/after {effective_from}."). *Backend:* already available from `getActiveExpectedBaseline` + the expected read state; add source-basis status (View 7).

**View 2 — Draft baseline review.** Full source-backed basis: module qty/wattage/degradation; inverter count/rating/efficiency; DC/AC ratio; thermal coefficient; losses + availability; PTO/operation dates; weather/irradiance model inputs; design-vs-as-built status; source doc/file/version; fact provenance; reviewer override/assumption status. For each field: raw value, normalized/canonical value, unit, evidence, confidence (where relevant), source doc/version, override reason + reviewer, and **whether it is baseline-driving**. Each field is tagged one of: **active fact**, **approved unknown**, **reviewer override**, **reviewer-supplied constant**, or **missing**. *Backend:* mostly present in the draft header + `field_sources`; the **5 reviewer-supplied constants** must be explicitly badged as "reviewer-supplied (no fact source)."

**View 3 — Physics validation & warnings.** Render the validation outcome **before** approval, never behind a generic pass/fail chip. Show blocking errors and warnings separately; for each: exact physics rule, affected field(s), expected impact, the warning policy, and whether acknowledgement is required. Acknowledgement (for warning-only baselines) requires the reviewer to type a source note. *Backend:* `validation_result_json` already carries the verdict; expose its rule/field detail to the panel.

**View 4 — Approval workflow.** Requires: permission (telemetry-admin **and** company-admin — fix the FE gate, §D); complete/non-blocking validation; explicit reviewer action; optional approval note; recorded identity + timestamp + baseline version. Plainly distinguishes **approved ≠ active**. *Decision needed:* separation-of-duties (§D.3).

**View 5 — Activation workflow.** Requires: approved baseline; **explicit effective date/time** (new control); downstream-impact confirmation; period-effective preview; confirmation that future buckets use the new baseline; no mutation of prior periods; an activation audit event. Confirmation copy (verbatim): *"Expected values before the effective date remain associated with prior active baseline versions. Expected values after the effective date will use this approved baseline, subject to normal availability and validation rules."* The panel already shows period-effective language; this view adds the explicit effective-date input and an audit event.

**View 6 — Preview / compare (read-only).** Current active vs proposed: changed inputs (already via `getBaselineDiff`), expected-production impact by interval, the effective-date boundary, impacted O&M periods, and gaps/unavailable periods — **no fabricated forecast** where inputs are missing. This view needs the **draft preview** unlock (extend `_PREVIEWABLE_BASELINE_STATUSES` to allow a read-only draft compute that persists nothing) plus a curve overlay on top of the existing field-diff table. Decision-support only; never an auto-recommendation.

**View 7 — Staleness & source-basis review.** Responds when an upstream document version changes, promoted facts change, a source file is replaced, a weather declaration changes, a device inventory/mapping change touches baseline-driving inputs, or a design/as-built source is superseded. Shows: "active baseline source basis changed"; the exact changed source/fact; whether expected output remains available; whether the baseline is still usable / stale / invalid; the required reviewer action; and links to source evidence + the reconciliation issue. **Do not auto-deactivate or alter active baseline math.** *Backend:* add a read-only "basis drift" comparison (mirror the weather `needs_re_review` fingerprint pattern) that diffs the active baseline's stored basis snapshot vs current promoted facts; surface, don't mutate.

**View 8 — History & audit trail.** Baseline lineage: draft → approval → activation → supersession → validation acknowledgements → stale/review events → effective dates → reviewer identities → source-basis snapshot → evidence links. Historical records are **read-only**. *Backend:* introduce a discrete (append-only) baseline event log OR a read-only assembler that reconstructs events from columns + `validation_result_json` + the supersession chain.

---

## C. Taxonomy, field model, validation, state machine, staleness model

### C.1 Status taxonomy (UI lifecycle state)

UI state is a function of `status` + effective dating + read-time validation + basis-drift:

| UI state | Derivation |
|---|---|
| No baseline | no rows for (site, weather_adjusted_model) |
| Draft | `status=draft` |
| Awaiting review | `status=in_review` (enum exists; **no transition endpoint yet**) |
| Validation warning | latest reviewable baseline whose `validation_result_json` has warnings unacknowledged |
| Approved (awaiting activation) | `status=approved` |
| Active | `status=active`, `active_to IS NULL` |
| Superseded | `status=superseded` (has `active_to`) |
| Stale / needs review | `status=active` AND basis-drift detected (View 7) — **proposed; no flag today** |
| Invalid | active (or owning segment) fails read-time `validate_baseline` → `baseline_invalid` |
| Rejected | `status=rejected` (enum exists; **no transition endpoint yet**) |

### C.2 Field-level review model

Per field, the panel must render: `raw_value` · `normalized_value` · `unit` · `evidence` · `confidence?` · `source_document/version` · `override_reason + reviewer?` · `is_baseline_driving`. Field **source class** ∈ { active_fact, approved_unknown, reviewer_override, reviewer_supplied_constant, missing }. Hazards to preserve: module_wattage is **W**, inverter_wattage is **kW** (never auto-convert); percent fields stored as percent and `/100` exactly once; loss signs normalized on import; text-with-unit facts (`"340 Wp"`) need confirm-only normalization carrying BOTH `source_fact_id` + `raw_value`. The 9 `REQUIRED_PHYSICS_FIELDS` are only 4 fact-backed (module/inverter wattage+qty); the other 5 are reviewer-supplied and must be visibly badged as such.

### C.3 Validation / warning handling

- Blocking (`hard_invalid`): activation refused (409 JSONResponse); read suppresses expected to null per owning segment; never auto-corrected — replacement is a new baseline.
- Warning: activation allowed only with `acknowledge_warnings=true` + `activation_source_note`. UI must show rule + field + expected impact per warning before the reviewer acknowledges.
- Never bury warnings behind a generic pass/fail chip (View 3).

### C.4 Approval & activation state machine

```
            create-draft-from-facts
                     │
                     ▼
                 [ draft ] ──(reject? proposed)──▶ [ rejected ]   (enum exists, no endpoint)
                     │
        (submit for review? proposed)
                     ▼
               [ in_review ]                       (enum exists, no endpoint)
                     │
              approve (telemetry-admin AND company-admin;
                       validation non-blocking; SoD? §D.3)
                     ▼
               [ approved ]  ──────────────────────────────┐ approved ≠ active
                     │                                      │
              activate (approved-only; explicit effective   │
                       date proposed; warnings ack'd)        │
                     ▼                                       │
   supersede prior active  ◀── single-active index + FOR UPDATE
                     ▼
                [ active ] ──(new activation supersedes)──▶ [ superseded ]
                     │
          (no standalone supersede / deactivate today — proposed)
```

Invariants enforced today: approval is not activation; activation is explicit + effective-dated; new activation never rewrites prior periods (period-effective read); invalid never supplies expected; no automatic activation/approval; historical rows immutable.

### C.5 Staleness / supersession model (proposed, read-only)

- **Basis snapshot at activation:** persist a hash/snapshot of the baseline-driving fact ids + values + source doc/version at approval/activation (mirror weather `upstream_fingerprint_json`).
- **Drift detection (read-only):** compare snapshot vs current promoted facts on read; if changed, surface UI state **Stale / needs review** + the exact changed fact/doc + required action. **Never auto-deactivate**, never alter math.
- **Supersession stays explicit** via a new activation (replacement). Optionally add a standalone supersede/retire-with-reason for the "wrong but no replacement yet" case — flagged as a product decision, not built in this sprint.

---

## D. Permissions & safety

### D.1 Permission matrix (verified)

| Action | Backend gate (true) | Frontend gate | Aligned? |
|---|---|---|---|
| View baseline / list / active | `get_authorized_site` (view) | tab-level `Diligence.view` / O&M view | Yes |
| Readiness (from facts) | `telemetry_admin_required` | `useTelemetryAdminPermission` | Yes |
| Create draft (from facts / legacy) | telemetry-admin **AND** company-admin (`get_authorized_site_with_company_admin`) | `useTelemetryAdminPermission` (telemetry-admin only) | **No — FE omits company-admin** |
| Edit draft / generate design points | `telemetry_admin_required` | `useTelemetryAdminPermission` | Yes |
| Diff / compare | telemetry-admin **AND** company-admin | `useTelemetryAdminPermission` | **No** |
| Approve | telemetry-admin **AND** company-admin | `useTelemetryAdminPermission` | **No** |
| Activate | telemetry-admin **AND** company-admin | `useTelemetryAdminPermission` | **No** |
| Acknowledge warning | (within activate) telemetry-admin **AND** company-admin | `useTelemetryAdminPermission` | **No** |
| Expected preview (curve) | `get_authorized_site` (view) | O&M view | Yes (but refuses draft) |
| Promote facts (source basis) | `Diligence:edit` (company-admin) | promote UI gate | Yes |
| View audit history | `get_authorized_site` (view) / `Diligence:view` | tab-level | Yes |

### D.2 The live permission defect
Create/approve/activate/diff require **both** telemetry-admin and company-admin on the backend, but `useTelemetryAdminPermission` checks only telemetry-admin. A telemetry-admin-without-company-admin user passes the FE gate, attempts the action, and receives a 403. **Fix (FE-only, no backend change):** extend the FE predicate for these actions to require company-admin too, and show a graceful read-only note otherwise.

### D.3 Separation of duties (explicit product decision required)
`crud.approve` stamps `reviewed_by` and `approved_by` to the same caller with **no check that approver ≠ creator/reviewer**. There is **no existing SoD policy**. Per the brief, this must be surfaced as an explicit product decision rather than invented. Options: (a) no SoD (status quo — document it); (b) soft SoD (warn + require a note when approver == creator); (c) hard SoD (block self-approval). Recommend deciding before building View 4.

### D.4 Other safety notes
- Structured errors (validation 409, freshness 409, review-required 422) MUST be returned as `JSONResponse`/response-model bodies — the global `http_exception_handler` `str()`s `HTTPException.detail` and destroys machine-readable payloads.
- Activation attribution is JSONB-only today (queryability gap) — View 8 should not depend on a column that doesn't exist.

---

## E. Site 4 walkthrough (controlled example — verified against the live DB)

Site 4 (110 Shawmut) has **two** weather-adjusted baselines and **no** design-estimate baseline.

| Field | Baseline #3 (v1) | Baseline #4 (v2) |
|---|---|---|
| Status | **superseded** | **active** |
| Type | weather_adjusted_model | weather_adjusted_model |
| Source | diligence_ai_parse | diligence_ai_parse |
| `active_from` | 2026-05-11 00:00 (= PTO, PTO-anchored first activation) | 2026-06-20 16:33:48.801667 |
| `active_to` | 2026-06-20 16:33:48.801667 | NULL |
| `supersedes_baseline_id` | — | 3 |
| `thermal_coefficient_pct` | **350.0 (physically impossible)** | **-0.35 (corrected)** |
| `pto_date` | 2026-05-11 | 2026-05-11 |
| reviewed_by / approved_by / created_by | 1 / 1 / 1 | 1 / 1 / 1 |
| `source_document_id` / `source_project_fact_id` | 912 / 114 | **NULL / NULL** |
| `validation_policy_version` | **NULL** (predates the gate) | `baseline-physics-v1` |
| stored points | 0 (computes on read) | 0 (computes on read) |

**Narrative:**
1. **Superseded invalid history (#3):** created/activated **before** the physics validation gate existed (`validation_policy_version` is NULL), which is precisely how thermal=350 got through historically. It owns buckets 2026-05-11 → 2026-06-20 16:33.
2. **Corrected active baseline (#4):** thermal corrected to -0.35; activated as a **replacement** (so `active_from = now = #3.active_to`, an exact clean handoff — no gap, no overlap), `validation_policy_version=baseline-physics-v1`. **Provenance regression to flag:** #4 lost the document/fact linkage (`source_document_id`/`source_project_fact_id` are NULL) that #3 had — it was created via the reviewer-supplied path without a single resolving document. The proposed View 2 must badge #4's fields accordingly.
3. **Period-effective expected behavior:** for a window spanning both, buckets ≤ 2026-06-20 16:33 are owned by #3 and are suppressed to `baseline_invalid` (expected null, actual/weather preserved, `invalid_baseline_segments` lists #3); buckets after are computed from #4. Overall `expected_state=partial`. This is the validate-on-read per-segment suppression that prevented #3 from emitting a ~−39,000 kW curve and flattening the actual line.
4. **Weather-governance state:** expected depends on measured **irradiance (POA)** + **cell temperature** resolved by `WeatherResolver` from V2 DAS rollups only. Site 4's weather semantics default to `unknown`, so unless `weather_device_mappings` declare POA/cell with full window coverage and no overlapping unknown, the window resolves `legacy_das_unverified` — numbers byte-identical to direct rollup reads, provenance never feeds the formula, **no GHI→POA / ambient→cell conversion**. The baseline UX must communicate this dependency and the `unverified` semantics **without claiming WS.5 weather integration**.
5. **What a reviewer would see before approving/activating a new Site 4 baseline (target UX):** status summary (active = #4 v2), the draft field table with provenance + reviewer-supplied badges, the physics verdict (must be non-blocking; warnings need ack + note), a diff vs #4, a **draft-curve preview** (currently blocked — preview refuses draft), an **explicit effective-date** confirmation (currently server-decided), and the period-effective immutability statement.

---

## F. Implementation phases (proposed; no build in this sprint)

- **Phase 0 — Safety alignment (FE-only, smallest blast radius).** Fix the FE permission predicate so create/approve/activate/diff require company-admin (match the backend). Decide SoD policy (§D.3) and reflect it in copy. No backend change.
- **Phase 1 — Decision-support preview (read-only).** Extend preview to allow a **draft** compute that persists nothing (`_PREVIEWABLE_BASELINE_STATUSES` + a `persist=false` draft path), then add a curve overlay to the existing diff table (View 6). Reviewer can finally see the curve before approving.
- **Phase 2 — Validation/warning surfacing (View 3).** Expose `validation_result_json` rule/field/impact detail in the panel; require per-warning visibility before acknowledgement.
- **Phase 3 — Explicit activation effective date + activation audit event (View 5, View 8).** Add an explicit effective-date control (default = current server behavior) and a discrete, append-only baseline event log (or a read-only event assembler). Promote activation attribution out of JSONB into the event log.
- **Phase 4 — Staleness / source-basis review (View 7).** Persist a basis snapshot at approval/activation; add a read-only drift comparison (mirror weather `needs_re_review`); surface "Stale / needs review" + changed fact/doc + required action + evidence links. No auto-deactivation.
- **Phase 5 — History & lineage (View 8 completion).** Field-level cross-version lineage; full read-only audit timeline.
- **Phase 6 (optional, product decision) — standalone supersede / retire-with-reason** for the "wrong but no replacement" case.

Each phase is additive, read-mostly where possible, and preserves: frozen physics math, no auto lifecycle transitions, no historical rewrite, period-effective selection, never-fabricate (null not 0).

## G. Browser-validation & regression-test plan

**Browser validation (Site 4 as the fixture):**
1. Status summary shows active = #4 v2, effective_from 2026-06-20, period-effective note present.
2. O&M actual-vs-expected over a window spanning both baselines shows expected null (no garbage) for the #3 segment, computed expected for the #4 segment, `BaselineInvalidBanner`/invalid-segment provenance for #3, and a healthy (non-flattened) actual line.
3. Draft review (create a throwaway draft from facts) renders every field with raw→normalized→unit→source + reviewer-supplied badges for the 5 constants.
4. Validation view shows the thermal rule explicitly for a deliberately-invalid draft; activation is refused (409) and both draft + active are untouched.
5. Warning-only draft cannot activate without ack + source note.
6. Preview (Phase 1) renders the draft curve and the active-vs-proposed overlay with an effective-date boundary and no fabricated values in missing-input periods.
7. Activation (Phase 3) requires an explicit effective date, writes an audit event, supersedes the prior active with a clean handoff, and rewrites no prior period.
8. Permission: a telemetry-admin-without-company-admin user is correctly gated in the FE (Phase 0) and never reaches a backend 403.

**Regression tests (must stay green):**
- Period-effective selection (`get_baselines_effective_in_window`) boundary/overlap/abutting cases.
- Validate-on-read per-segment suppression (valid+invalid → partial; all-invalid → baseline_invalid; company active-only path unchanged).
- Activation fail-closed: hard_invalid blocks via JSONResponse; draft + active untouched.
- Single-active partial unique index + FOR UPDATE supersede.
- create-draft-from-facts honesty: missing/non-numeric required field → 422 body (not raised HTTPException); no defaults fabricated; draft-only; existing active untouched.
- Promotion freshness guard (baseline-driving stricter; structured 409).
- Never-fabricate: expected null never 0 at site/company/device levels.
- Frontend: `DraftBaselineReviewPanel.test.tsx`, `Reconciliation.test.tsx`, `BaselineFromFactsPanel` tests, and any new preview/effective-date/staleness tests.
- Site 4 protected-row fingerprint unchanged by any backfill/classification scripts.

---

## H. Hard-constraint compliance checklist (this sprint)

- [x] No baseline math/formula changes — audit only.
- [x] No automatic draft/approve/activate/supersede/deactivate proposed.
- [x] No historical expected rewrite — period-effective immutability reaffirmed.
- [x] No BigQuery/Firestore/SAFL/legacy as operational truth — SAFL create path stays deprecated; truth = project_facts → baseline.
- [x] No weather-semantic inference — unknown stays unknown; no GHI→POA/ambient→cell.
- [x] No WS.5 work — weather dependency is communicated, not integrated.
- [x] No production code changes — this document is the only artifact.
