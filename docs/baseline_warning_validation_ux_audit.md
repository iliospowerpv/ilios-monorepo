# Baseline Warning & Validation UX — Audit & Phase B2 Implementation Plan

**Status:** AUDIT / DESIGN ONLY — no production code was written or changed. Implementation begins only after review and explicit approval.
**Date:** 2026-06-26
**Scope:** Audit the current baseline validation + warning workflow (draft → approve → activate) and design a reviewer-centered validation experience (Phase B2). Preserve all existing operational truth, lifecycle behavior, authorization (Phase 0), and expected-value integrity.

> **Authority model (unchanged from Phase 0).** Read validation / review draft = telemetry-admin + authorized site access. Approve / activate = telemetry-admin **AND** company-admin (or platform bypass). This sprint does **not** alter any authorization behavior.

---

## 1. Executive summary

The platform already has a **mature, fail-closed validation engine** for weather-adjusted (WA) expected baselines, but the **reviewer-facing experience is thin** relative to the richness of the data the engine produces. The engine computes a fully structured per-field + cross-field + smoke-test verdict (`validation_result_json`); the UI surfaces only a flat warnings list, a single thermal-coefficient inline check, and a 409-driven acknowledgement dialog. The reviewer is therefore asked to **approve before seeing the curve** (historically) and to **acknowledge warnings without grouped severity, field-level highlighting, evidence links, or source-basis context**.

Key facts established by this audit:

- **One canonical validation module** (`baseline_physics_validation.py`) is the single source of truth. It is **pure** (no DB writes, no unit conversions, no auto-correction). Everything else either *calls it to gate a write* (activation) or *calls it to suppress a read* (O&M / preview).
- **Validation never mutates operational truth.** The only place validation *state* is persisted is on **activation**, when the verdict is stamped onto the activated row's `validation_result_json` in the same transaction. Every other consumer is read-only.
- **`hard_invalid` is absolute.** No acknowledgement, note, or reviewer action can waive a `hard_invalid` physics verdict — enforced server-side in `crud.activate` **before** any supersede/commit.
- **Warnings are waivable only with an explicit note.** `acknowledge_warnings=true` **plus** a non-empty `activation_source_note` is required to activate a warning-only baseline; the waiver is recorded on the row.
- **Site 4 / 110 Shawmut is the canonical protected case.** Its superseded baseline #3 (`thermal_coefficient_pct=350`) defines the `hard_invalid` band and is handled by **validate-on-read suppression** (never mutated, never a fabricated curve). Phase B2 introduces **no operational change to Site 4**.
- **The biggest decision-support gaps are presentational, not computational.** Grouped severity, field-level highlighting, evidence/source-basis links, an activation-readiness summary, and validation-history visibility are all **display layers over data the backend already computes** (surfaced today via the diff endpoint's `from_validation`/`to_validation`, the activation structured-409 body, the draft-preview `validation_summary`, and the stored row; note the list/active responses currently carry only a compact `baseline_validation_summary`, not the full report — see §8). Phase B2 can deliver real reviewer value with **zero changes to validation rules, physics, math, lifecycle, or permissions**.

Phase B2 is therefore scoped as a **read/display + capture-UX** sprint: present the existing verdict better, capture reviewer intent more deliberately (notes where appropriate), and make the warning/blocking taxonomy legible — without touching how any verdict is computed or how any baseline transitions.

---

## 2. Current validation architecture

### 2.1 The single validation engine (pure, read-only)

`backend/ilios-server/app/services/telemetry/baseline_physics_validation.py` (957 lines).

- Entry point: `validate_baseline(baseline, validation_source_mode=...)` → `BaselineValidationReport`.
- **Never** mutates, converts, auto-corrects, or persists. Callers decide what to do with the verdict (module docstring lines 1–29).
- Policy identity is persisted with every verdict: `POLICY_VERSION = "baseline-physics-v1"`, `TEMPERATURE_UNIT_CONTRACT_VERSION = "tc-contract-v1"` (lines 50–60). Bumping the contract is the mechanism that prevents a stored verdict from being silently reinterpreted under a different contract.
- Two anchoring design rules (lines 13–28): **one canonical temperature-unit contract** (`%/°C`; Fahrenheit converted exactly once via `(F−32)/1.8` in `expected_service._expected_power_breakdown`) and **never guess or convert** (ambiguous units are `warning`, never auto-reinterpreted).
- Imports the **frozen** physics core from `expected_service` (`BaselineParams`, `REQUIRED_PHYSICS_FIELDS`, `_expected_power_breakdown`, baseline constants) — lines 38–44 — so the smoke test exercises the *same* code path production uses.

### 2.2 The two enforcement points (compute) vs. everyone else (display)

| Point | File / function | Mode | Effect |
| --- | --- | --- | --- |
| **Activation gate (WRITE)** | `app/crud/telemetry_expected.py::TelemetryExpectedBaselineCRUD.activate()` (line 317) | `validation_source_mode="activation_gate"` | Runs **before** supersede/commit. `is_blocking` → hard block; warnings → require ack + note. Stamps verdict onto the row. **The only place a verdict is persisted.** |
| **Read-time suppression (READ)** | site: `app/services/telemetry/expected_service.py::compute_site_expected()`; company: `app/helpers/telemetry/v2_company_data.py` (`_summarize_site_expected`, `is_active_baseline_blocking`); O&M chart seams `app/helpers/telemetry/v2_chart_data.py` (`_active_baseline`, `_evaluate_active_baseline`); preview endpoint default-active path | `validation_source_mode="read_time"` | Validates the **current active** baseline (and every period-effective segment) on read. Blocking → state `baseline_invalid`, expected suppressed to NULL (**never 0**), actuals preserved. **No mutation.** |

### 2.3 Period-effective stitching

`crud.get_baselines_effective_in_window` (consumed by `expected_service.compute_site_expected`) validates **every overlapping segment** at read time. A superseded-but-invalid segment inside the window is suppressed per-bucket (`baseline_invalid`: expected NULL, actual/weather preserved verbatim, owning `baseline_id` stamped) — it never computes physics and never emits a garbage expected curve. Suppression is read-only and fail-closed.

### 2.4 Where validation STATE can change vs. where it is merely displayed

- **State can change (write) in exactly one place:** `crud.activate()` stamps `validation_result_json` + `validation_policy_version` in the activation transaction. There is **no** other write path for validation state.
- **Everywhere else is display/read:** the readiness endpoints, the diff endpoint, the active/list endpoints, the expected-preview + draft-preview endpoints, the O&M chart/company aggregation read paths, and every frontend component **read** validation but never persist it.

---

## 3. Validation rule inventory

All rules live in `baseline_physics_validation.py` and source their required-field set from `expected_service.REQUIRED_PHYSICS_FIELDS`.

### 3.1 Completeness / readiness (input presence)

- `REQUIRED_PHYSICS_FIELDS` (expected_service.py): the 9 inputs the WA model needs — `module_wattage`, `module_quantity`, `inverter_wattage`, `inverter_quantity`, `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct`.
- **Source asymmetry (durable, non-obvious):** only the 4 module/inverter wattage+quantity fields are fact-backed (`FACT_FIELD_TO_COLUMN`). `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct` are **reviewer-supplied-only** (no extraction, no reconciliation row today).
- **PTO is required for `weather_adjusted_model`:** a NULL `pto_date` suppresses the **entire** curve (every bucket `pre_pto`, expected NULL), so a WAM draft cannot be created without it.
- Readiness is computed by `baseline_from_facts_service.evaluate_readiness` (surfaced by the readiness-from-facts endpoint), distinct from the physics verdict.

### 3.2 Per-field physics bounds (single source of truth: `EXPECTED_UNITS` + per-field classifiers)

| Field | Unit (`EXPECTED_UNITS`) | `hard_invalid` | `warning` |
| --- | --- | --- | --- |
| `thermal_coefficient_pct` | `% per °C` | positive / non-physical magnitude (e.g. `350` — Site 4 #3) | sign/magnitude near a `%/°F`-vs-`%/°C` mismatch (e.g. ~−0.63), unusually small (e.g. −0.2) |
| `module_wattage` | `W (per module)` | outside ~50–1000 W | near-edge plausibility |
| `inverter_wattage` | `kW AC (per inverter)` | non-positive | possible W-in-kW magnitude |
| `inverter_quantity` / `module_quantity` | `count` | non-positive | — |
| `power_tolerance_min_pct` | `% (≤ 0)` | positive | edge values |
| `cec_efficiency_pct` | `%` | outside ~50–105% | near edges |
| `year_1_degradation_pct` | `%` | > ~5% | elevated |
| `annual_degradation_pct` | `%` | > ~3% | elevated |

### 3.3 Cross-field checks (`cross_field_checks[]`)

- **DC/AC ratio:** `hard_invalid` outside ~0.7–2.0; `warning` outside ~0.9–1.6.
- **Aggregate AC-side loss total:** `hard_invalid` when ≥ ~50%; single loss > ~15% → `warning`.

### 3.4 Smoke test (`smoke_test{}`)

`run_smoke_test()` exercises the **production** `_expected_power_breakdown` across a temperature grid (≈0–65 °C), asserting: Celsius/Fahrenheit equivalence (25 °C == 77 °F → temperature factor 1.0), monotonic temperature factor behavior, and a deliberate **unit-mismatch demonstration**. `SmokeTestReport.has_blocking` is true if any `hard_invalid` check fails.

> Exact bound constants are intentionally summarized here rather than copied, because **Phase B2 changes none of them** — they remain the frozen contract owned by `baseline_physics_validation.py`.

---

## 4. Severity classification matrix

`Classification` enum (lines 67–72): `plausible`, `warning`, `hard_invalid`. **`hard_invalid` is the only blocking verdict.**

| Engine verdict | Aggregated as | Blocks activation? | Waivable? | Read-time effect on active baseline |
| --- | --- | --- | --- | --- |
| `hard_invalid` (any field / cross-field / failed smoke check) | `is_blocking = true` | **Yes** | **Never** | `baseline_invalid` — expected curve suppressed (NULL, never 0); actuals preserved |
| `warning` (one or more) | `has_warnings = true`, `is_blocking = false` | No | Yes — `acknowledge_warnings=true` **+** non-empty `activation_source_note` | Computes normally (warnings are advisory) |
| `plausible` only | not blocking, no warnings | No | n/a | Computes normally |

**Proposed Phase B2 presentation states** (display-only mapping over the existing verdict — no new engine states): `ready`, `available`, `warning`, `blocked`, `invalid`, `partial`, `unavailable`, `needs review`. These map deterministically from existing data: `is_blocking` → `blocked`/`invalid`; `has_warnings` → `warning`; readiness gaps → `needs review`/`unavailable`; `expected_state` (`available`/`partial`/`missing_inputs`/`pre_pto`/`baseline_not_available`) → `available`/`partial`/`unavailable`.

---

## 5. Blocking vs. warning analysis

The blocking/warning decision is made in **two distinct contexts**, never conflated:

1. **Activation context (write gate)** — `crud.activate()` lines 346–357:
   - `report.is_blocking` → `BaselinePhysicsBlockedError(reason="hard_invalid")` — outright block, no commit.
   - `report.has_warnings and not acknowledge_warnings` → `reason="warnings_require_ack"`.
   - `report.has_warnings and acknowledge_warnings and not note` → `reason="source_note_required"`.
   - Only after all three pass does supersede + activate run. **On any block, the draft and the existing active row are untouched (no commit).**
2. **Read context (suppression)** — an already-active baseline later judged `is_blocking` (e.g. after a policy bump) is suppressed on read (`baseline_invalid`) but **never blocked from being read and never mutated**.

The router (`activate_expected_baseline`, line 3851) translates a `BaselinePhysicsBlockedError` into a **structured 409 via `JSONResponse`** (`_baseline_block_body(exc)`) so the full validation report reaches the client unflattened; a plain status error (e.g. "not approved") is a standard 409. Approve (`approve_expected_baseline`, line 3810) has **no physics gate** — physics is enforced only at activation.

---

## 6. Current reviewer workflow

End-to-end, as it exists today:

1. **Create draft** — `BaselineFromFactsPanel.tsx` (from promoted facts) or the manual create endpoint. Inline thermal-coefficient classification (`classifyThermalCoefficientPct` → plausible/warning/hard_invalid) disables "Create Draft" on `hard_invalid`. Drafts are never auto-approved/activated.
2. **Review readiness** — `ReadinessSummary.tsx` shows `facts_to_draft_ready` (BoolPill), `missing_required_physics_fields` (chips), and a flat warnings list.
3. **Preview** — `DraftPreviewOverlay.tsx` (Phase 1) now renders a read-only draft-vs-active dual-line chart with honest NULL gaps; `baseline_invalid` suppresses the curve (`draft-preview-overlay-suppressed`). (Historically reviewers could **not** preview a draft curve — that hole is now partly closed for telemetry-admins.)
4. **Approve** — `DraftBaselineReviewPanel.tsx`, gated on `canManageLifecycle` (from the active-baseline envelope's `viewer_can_manage_lifecycle`). Stamps reviewer + approver. No physics gate here.
5. **Activate** — same panel. Fail-closed physics gate. On a 409 the panel opens an acknowledgement section: a warning Alert (server `message` + `warning_fields`), a mandatory `activation_source_note` (`activate-source-note`), and the button relabels to "Acknowledge & activate". `hard_invalid` cannot proceed.
6. **Read-only fallback** — when the viewer lacks lifecycle rights, approve/activate render disabled with a tooltip and a `lifecycle-readonly-explanation`.

Existing reviewer-intent capture: `activation_source_note` (waiver rationale on warning activation) and the baseline `notes` column. There is **no** general approval note, no per-field override note, and no field-level reviewer annotation.

---

## 7. UX gaps (missing reviewer decision support)

1. **No grouped/severity-ranked validation panel.** Warnings are a flat list or scattered chips; `blocking_field_count` / `warning_field_count` and the per-field `reason` / `required_action` already returned by the engine are not assembled into one severity-ordered summary.
2. **No field-level highlighting.** `validation_result_json.fields[]` carries `field`, `classification`, `reason`, `required_action`, but the `ReconciliationTable` cells and `BaselineFromFactsPanel` inputs are not highlighted from it (only the inline thermal check exists).
3. **No evidence/source links.** Baseline-level provenance exists (the verdict's `provenance` carries `source_document_id` + `source_project_fact_id`; richer document-version / AI-run / document-key lineage lives on the reconciliation rows + project-fact lineage, **not** inside `validation_result_json.fields[]`) but there is no deep link from a failing physics field to the originating Data Room page/snippet.
4. **No source-basis visibility.** Reviewers cannot see at a glance which physics inputs are fact-backed vs. **reviewer-supplied-only** (the 5 constants), nor which were normalized from text-with-unit facts.
5. **Thin reviewer guidance.** Only tooltips + one "how to read this view" alert; the engine's per-field `required_action` text is not surfaced as actionable "how to fix" guidance.
6. **Acknowledgement UX is coarse.** A single source-note covers *all* warnings at once; there is no per-warning acknowledgement, and no preview of *what will change* on activation.
7. **No activation-readiness summary.** There is no single "what happens if I activate now" panel (blocking count, warnings to acknowledge, missing inputs, PTO presence, design-points status, what gets superseded).
8. **No validation-history visibility.** `validation_result_json` is stamped per activation but prior versions' verdicts and the waiver trail are not surfaced; the diff is a field table only.
9. **Required notes are under-scoped.** Notes are required only on warning activation — not for approval or for baseline-driving overrides where a rationale would aid the next reviewer.

---

## 8. API inventory (existing routes — unchanged)

All under `/api/telemetry/v2`, in `backend/ilios-server/app/routers/telemetry/v2.py`.

| Operation | Method | Path | Auth | Req / Res schema | Line |
| --- | --- | --- | --- | --- | --- |
| List / history | GET | `/sites/{site_id}/expected-baselines` | `telemetry_admin_required` | → `ExpectedBaselineListResponse` (+ `viewer_can_author_draft`, `viewer_can_manage_lifecycle`) | 3081 |
| Get active | GET | `/sites/{site_id}/expected-baselines/active` | `get_authorized_site` | → `ActiveExpectedBaselineResponse` (+ viewer flags) | 3110 |
| Create draft (manual) | POST | `/sites/{site_id}/expected-baselines` | `telemetry_admin_required` | `ExpectedBaselineCreateRequest` → `ExpectedBaselineResponse` | 3149 |
| Readiness from facts | GET | `/sites/{site_id}/expected-baseline/readiness-from-facts` | `telemetry_admin_required` | → `ReadinessFromFactsResponse` | 3251 |
| Create draft from facts | POST | `/sites/{site_id}/expected-baseline/create-draft-from-facts` | `telemetry_admin_required` | `CreateDraftFromFactsRequest` → `CreateDraftFromFactsResponse` (422 readiness body if not ready) | 3287 |
| Diff | GET | `/expected-baselines/{baseline_id}/diff` | `telemetry_admin_required` | → `BaselineDiffResponse` | 3548 |
| Design-points readiness | GET | `/sites/{site_id}/expected-baseline/{baseline_id}/points-readiness` | `telemetry_admin_required` | → `DesignPointsReadinessResponse` | ~3634 |
| Generate design points | POST | `/sites/{site_id}/expected-baseline/{baseline_id}/generate-design-points` | `telemetry_admin_required` | → `GenerateDesignPointsResponse` | ~3660 |
| **Approve** | POST | `/expected-baselines/{baseline_id}/approve` | `telemetry_admin_required` + `enforce_baseline_lifecycle_authority(action="approve")` | → `ExpectedBaselineResponse` | 3810 |
| **Activate** | POST | `/expected-baselines/{baseline_id}/activate` | `telemetry_admin_required` + `enforce_baseline_lifecycle_authority(action="activate")` | `BaselineActivateRequest` → `ExpectedBaselineResponse`; **structured 409** on physics block | 3851 |
| Expected preview (O&M / public-ish) | GET | `/sites/{site_id}/expected-preview` | `get_authorized_site` | → `ExpectedPreviewResponse`; explicit `baseline_id` must be in `_PREVIEWABLE_BASELINE_STATUSES` (approved/active/superseded) else 409; default-active validates on read → `baseline_invalid` | 3916 |
| Draft preview (Phase 1) | GET | `/sites/{site_id}/expected-baseline/{baseline_id}/draft-preview` | `telemetry_admin_required` + site access | → `DraftExpectedPreviewResponse`; `draft`/`approved` only (409 else), 404 cross-site, validate-on-read | ~3990+ |

`BaselineActivateRequest` (schema line 1157): `acknowledge_warnings: bool = False`, `activation_source_note: Optional[str]` (max 2000). The structured 409 body is built by `_baseline_block_body(exc)` carrying `reason` ∈ {`hard_invalid`, `warnings_require_ack`, `source_note_required`} plus the full report.

**Where the FULL validation verdict is exposed (read):** the diff response (`from_validation` / `to_validation`), the activation structured-409 body, and the draft-preview `validation_summary`. The list/active/`ExpectedBaselineResponse` payloads expose only a compact `baseline_validation_summary` (not the full `validation_result_json`), and the readiness endpoints return readiness `field_blockers` + warnings (not a `BaselineValidationReport`). A B2 history/grouped surface therefore reads the stored rows directly and/or an optional read-only endpoint (see B2.10) — it must not assume the list/active payloads already carry the full per-field verdict.

**Phase B2 adds no new mutating route.** Any new endpoint would be **read-only** (e.g. a validation-history read) and would reuse existing auth dependencies.

---

## 9. Data model inventory (existing — unchanged)

`backend/ilios-server/app/models/telemetry_expected.py`.

- **`TelemetryExpectedBaseline`** (line 109) — immutable physics-snapshot header. Validation/workflow/audit columns:
  - `validation_result_json` (205, JSONB), `validation_policy_version` (206)
  - `version` (208), `reviewed_by` (210), `reviewed_at` (213), `approved_by` (214), `approved_at` (217)
  - `active_from` (218), `active_to` (219), `supersedes_baseline_id` (220, self-ref)
  - `created_by_user_id` (225), `notes` (228)
  - **No discrete `activated_by`/`activated_at` columns** — activation identity/time live inside `validation_result_json["activation"]` (`acknowledged_warnings`, `source_note`, `activated_by_user_id`, `activated_at`). JSONB-only → not queryable, no discrete event log. (The `activated_by`/`activated_at` columns that exist elsewhere belong to the weather module, not baselines.)
- **`TelemetryExpectedBaselinePoint`** (252) — stored design-estimate curve points (monthly/annual).
- **Enums:**
  - `TelemetryBaselineStatus` (70): `draft`, `in_review`, `approved`, `active`, `superseded`, `rejected`. **`in_review` and `rejected` have no endpoint that transitions into them today.**
  - `TelemetryBaselineType` (56): `design_estimate`, `weather_adjusted_model`, `imported_8760`, `manual`.
  - `TelemetryBaselineSource` (82): `pvsyst`, `design_document`, `diligence_ai_parse`, `manual_entry`, `imported_8760`, `legacy_formula`.

**`validation_result_json` shape** (from `BaselineValidationReport.to_dict()`, lines 202–221): `baseline_id`, `is_blocking`, `summary`, `policy_version`, `temperature_unit_contract`, `temperature_unit_contract_version`, `validation_timestamp`, `validation_source_mode`, `celsius_fahrenheit_equivalence_verified`, `blocking_field_count`, `warning_field_count`, `fields[]` (each: `field`, `entered_value`, `expected_unit`, `classification`, `reason`, `source`, `required_action`, `policy_version`), `cross_field_checks[]` (same shape), `smoke_test{}` (`ran`, `reason_not_run`, `celsius_fahrenheit_equivalence_verified`, `temperature_input_modes_exercised[]`, `probes[]`, `checks[]`, `unit_mismatch_demonstration`), `provenance{}` (baseline-level only — `source_document_id`, `source_project_fact_id`), and on activation an additional `activation{}` block.

**Audit-trail status:** `app/helpers/telemetry/audit.py::create_audit_log` (line 17) logs to `audit_logs` (`source="telemetry"`). The approve/activate router currently does **not** emit a discrete `audit_logs` entry for lifecycle transitions (the verdict + waiver are recorded only inside `validation_result_json`). This is an **observability gap**, not a correctness gap — flagged as an open decision (§18), implementable additively (read/write to the existing audit table, no schema change).

---

## 10. Frontend component inventory (existing)

Under `frontend/rea-investment-fe/src/modules/project-hub/pages/AssetManagementSiteDetails/tabs/Reconciliation/`:

| File | Component | Today's validation/warning rendering | Notable testids |
| --- | --- | --- | --- |
| `Reconciliation.tsx` | `Reconciliation` | Entry; fetches reconciliation + active baseline; computes `canEdit` (Diligence.edit), `canDraft` (`useTelemetryAdminPermission`), `canManageLifecycle` (active envelope flag) | `reconciliation-tab` |
| `components/ReadinessSummary.tsx` | `ReadinessSummary` | `facts_to_draft_ready` BoolPill, `missing_required_physics_fields` chips, flat warnings list | `reconciliation-readiness` |
| `components/BaselineFromFactsPanel.tsx` | `BaselineFromFactsPanel` | Inline thermal classification; disables Create Draft on `hard_invalid` | `baseline-from-facts-panel`, `thermal-verdict`, `thermal-preview` |
| `components/DraftBaselineReviewPanel.tsx` | `DraftBaselineReviewPanel` | Lists draft/approved/active; warnings from params; approve/activate; 409 ack workflow + source note; read-only explanation | `draft-baseline-detail`, `activate-confirm-dialog`, `activate-source-note`, `lifecycle-readonly-explanation` |
| `components/DraftPreviewOverlay.tsx` | `DraftPreviewOverlay` | Draft-vs-active dual-line chart; suppresses on `baseline_invalid`; honest NULL gaps | `draft-preview-overlay`, `draft-preview-overlay-suppressed`, `-disclaimer`, `-empty`, `-error` |
| `components/ReconciliationTable.tsx` | `ReconciliationTable` | Grid (AI / Accepted / Active Fact / Draft / Active Baseline); required-for-baseline star | `reconciliation-table`, `reconciliation-row`, `required-marker` |
| `components/ReconciliationTable.tsx` (inline `StatusCell`) | `StatusCell` | `status_label` + `blocking_level` chips; Promote / Create Task gated by `canAct` (defined inline within `ReconciliationTable.tsx`, not a separate file) | `reconciliation-blocking-chip`, `reconciliation-promote-btn` |

Supporting: `src/api/telemetryV2.ts` + `src/types/telemetryV2.ts` (client + types), `useTelemetryAdminPermission` hook (FE mirror of `telemetry_admin_required`).

---

## 11. Browser workflow (current)

1. Navigate Project Hub → site → Asset Management → **Reconciliation** tab.
2. `ReadinessSummary` + `ReconciliationTable` render; an admin sees `BaselineFromFactsPanel` + `DraftBaselineReviewPanel`.
3. Create draft → inline thermal verdict gates the button.
4. Open `DraftPreviewOverlay` (admin) to see draft-vs-active curve; suppressed if invalid.
5. **Approve** (lifecycle-admin) → status `approved`.
6. **Activate** (lifecycle-admin) → physics gate: clean activates immediately; warnings open the acknowledgement dialog (mandatory note); `hard_invalid` is blocked with the structured report; non-lifecycle viewers see the read-only explanation.
7. O&M / expected charts read the **active** baseline; an invalid active baseline shows `baseline_invalid` (suppressed expected, real actuals).

---

## 12. Test inventory (existing)

**Backend (`backend/ilios-server/tests/`):**

- `unit/telemetry/baseline_physics_validation_test.py` — per-field classification bands; cross-field (DC/AC ratio, aggregate AC losses); smoke-test F/C equivalence; aggregate `is_blocking`. Uses `350.0` as the canonical `hard_invalid` ("Site 4 #3") case (≈L202, L317, L359, L365, L403) and `−0.35` corrected (≈L409).
- `unit/telemetry/test_baseline_from_facts.py` — promoted-facts → draft bridge; readiness (missing required vs. supplied constants); provenance; only `draft` created; non-numeric facts block. Site-4 PTO / effective-from comments (≈L1040, L1132).
- `integration/test_baseline_lifecycle_endpoints.py` — approve/activate authority (telemetry-admin **AND** company-admin); draft-preview 200/409/404; invalid-baseline activation blocked. Runs on throwaway per-test sites only.
- `unit/telemetry/baseline_lifecycle_authorization_test.py` — deep lifecycle permission matrix.
- `unit/telemetry/test_readiness.py` — site-level readiness incl. V2 fallback.
- `unit/telemetry/period_effective_baseline_test.py` — superseded/historical semantics, `active_from`/`active_to`.
- `unit/telemetry/test_v2_expected_wiring.py` — physics-param wiring into the WA model.

**Frontend (`frontend/rea-investment-fe/src/`):**

- `.../Reconciliation/__tests__/DraftBaselineReviewPanel.test.tsx` — draft provenance; read-only preview overlay; approve/activate dialogs; warnings + PTO-suppressed; historical chips; read-only explanation.
- `.../Reconciliation/__tests__/Reconciliation.test.tsx` — table + readiness; field status chips; action gating.
- `utils/telemetry/__tests__/deviceDiagnostics.test.tsx`, `components/common/InventoryReconciliationChip/__tests__/InventoryReconciliationChip.test.tsx` — adjacent status/diagnostic rendering.

**Coverage gaps (for Phase B2):** no test asserts a *grouped/severity-ordered* presentation, field-level highlighting derived from `validation_result_json.fields[]`, evidence-link wiring, source-basis labeling, an activation-readiness summary, or validation-history rendering — because none of those surfaces exist yet.

---

## 13. Site 4 / 110 Shawmut validation assessment

- **Identity:** Site 4 = 110 Shawmut (HoldCo `Shawmut Solar Holdings, LLC`). Baseline **#3** superseded/invalid (`thermal_coefficient_pct = 350` — Watts-for-percent error); baseline **#4** active/corrected (`−0.35 %/°C`).
- **How it is protected today:** #3's value defines the `hard_invalid` band in `baseline_physics_validation.py`; the read paths **validate-on-read** and suppress #3 (and any invalid period-effective segment) to `baseline_invalid` — expected NULL, actuals preserved, **no mutation, no fabricated curve**. The classic symptom (a flat *actual* line caused by an invalid segment blowing up the shared Y-axis) is mitigated by per-segment suppression + the FE `finiteOrNull` domain guard.
- **Phase B2 stance:** **No operational change to Site 4.** Site 4 is used **read-only** for browser validation (render/forbidden/isolation/unchanged). **No approve/activate is ever performed on Site 4 in the live app or browser.** Any approve/activate happy-path is exercised only on throwaway pytest sites.

---

## 14. Recommended Phase B2 implementation plan

**Design principle:** Phase B2 is a **presentation + intent-capture** layer over the existing verdict. It computes nothing new about physics, changes no rule, no math, no lifecycle, and no permission. Every recommendation below is additive and read/display (the one optional write is an additive audit-log entry on existing lifecycle calls — see §18, gated on product approval).

### B2.1 Grouped validation panel (display)
A single reviewer panel that consumes the **existing** `validation_result_json` (or the live verdict from the diff/readiness responses) and renders fields grouped by severity: **Blocking (invalid)** → **Warnings** → **Informational/plausible**. Use `blocking_field_count` / `warning_field_count` for the header summary. No new backend compute.

### B2.2 Severity hierarchy + explicit states (display)
Adopt the explicit state vocabulary (`ready`, `available`, `warning`, `blocked`, `invalid`, `partial`, `unavailable`, `needs review`) as a deterministic mapping over existing flags (`is_blocking`, `has_warnings`, `expected_state`, readiness). One shared FE mapper so chips/labels stay consistent across `ReadinessSummary`, `DraftBaselineReviewPanel`, `StatusCell`, and the new panel.

### B2.3 Field-level highlighting (display)
Drive `ReconciliationTable` cell highlighting and `BaselineFromFactsPanel` input states from `validation_result_json.fields[]` (`field` → cell, `classification` → color, `reason`/`required_action` → tooltip). Keep the existing inline thermal check; generalize it from the same data.

### B2.4 Evidence links (display)
Where a physics field traces to a document, deep-link "View evidence" to the Data Room using the available provenance — the verdict carries baseline-level `source_document_id` / `source_project_fact_id`, and richer document-version / AI-run / document-key lineage is sourced from the reconciliation rows + project-fact lineage (not from `validation_result_json.fields[]`). For reviewer-supplied-only constants, show "Reviewer-supplied (no document source)" honestly — never fabricate evidence.

### B2.5 Source-basis visibility (display)
Per physics input, label the basis: **fact-backed**, **reviewer-supplied-only** (the 5 constants), or **normalized-from-text** (carry the normalization provenance already recorded on the baseline effective value). This directly addresses the "why is this missing?" confusion.

### B2.6 Reviewer guidance (display)
Surface the engine's per-field `required_action` as actionable "how to fix" copy next to each blocking/warning field, plus a short context-sensitive explainer for the three activation block reasons (`hard_invalid`, `warnings_require_ack`, `source_note_required`).

### B2.7 Acknowledgement UX (capture)
Upgrade the activation dialog: list each warning (from `warning_fields`) with the reason, require the reviewer to acknowledge the **set** of warnings, and keep the **mandatory** `activation_source_note`. Optionally show per-warning checkboxes for clarity. The backend contract is unchanged (`acknowledge_warnings` + `activation_source_note`); this is purely a richer client UX.

### B2.8 Required reviewer notes (capture, where appropriate)
Keep notes mandatory for warning activation (existing). **Recommend** (open decision §18) extending a *required rationale* to baseline-driving overrides; do **not** silently change the approve contract without product sign-off.

### B2.9 Activation-readiness summary (display)
A pre-activation "what happens if I activate now" summary: blocking count (must be 0), warnings to acknowledge, missing inputs, PTO presence, design-points status, and **which baseline gets superseded** (from `supersedes` resolution). Assembled entirely from existing responses.

### B2.10 Validation-history visibility (display; optional read endpoint)
Surface prior `validation_result_json` verdicts and the waiver trail (`activation` block: who/when/acknowledged/source-note) across versions, alongside the existing field diff. If the list/active responses do not already carry enough history, add a **read-only** history endpoint (reusing `telemetry_admin_required`) — no schema change, reads existing rows.

### Suggested sequencing
1. B2.2 shared state mapper (foundation) → 2. B2.1 grouped panel → 3. B2.3 field highlighting → 4. B2.5 source-basis + B2.4 evidence links → 5. B2.6 guidance → 6. B2.7 acknowledgement UX → 7. B2.9 readiness summary → 8. B2.10 history (+ optional read endpoint) → 9. B2.8 notes policy (pending product decision).

---

## 15. Risks

1. **Scope creep into the engine.** The strongest risk is "improving" a rule while building the display. Mitigation: Phase B2 touches **no** file under physics/expected compute; treat `baseline_physics_validation.py`, `expected_service.py`, and `crud.activate` as **frozen**.
2. **Fabrication via UI.** A grouped/severity view could imply a verdict the engine didn't give (e.g. coloring a `plausible` field as warning). Mitigation: map strictly from `classification`; render `unavailable`/`needs review` rather than guessing.
3. **Evidence-link over-claiming.** Linking a reviewer-supplied constant to a document would be fabricated provenance. Mitigation: only link when a real provenance ID exists; otherwise label honestly.
4. **Permission drift.** Re-deriving lifecycle capability client-side could diverge from Phase 0. Mitigation: keep gating on the backend `viewer_can_manage_lifecycle` / `useTelemetryAdminPermission`; never hand-roll.
5. **Site 4 regression.** Any browser step that activates on Site 4 would corrupt the protected case. Mitigation: Site 4 read-only in browser; lifecycle happy-path only on throwaway sites.
6. **Audit-log addition (if approved) writing in the wrong transaction.** If B2.10's optional audit entry is built, it must be best-effort and must never block or roll back a successful/failed lifecycle transition. Mitigation: write audit after the lifecycle outcome, isolated from the activation transaction.

---

## 16. Mutation boundaries

**Allowed to change in Phase B2 (when implemented later, after approval):**
- Frontend display components and shared mappers/types (read-only rendering of existing data).
- Frontend activation-dialog UX (still sending the **existing** `acknowledge_warnings` + `activation_source_note` contract).
- *Optional, product-gated:* one additive **read-only** validation-history endpoint and/or one additive best-effort `audit_logs` write on existing approve/activate calls — **no schema change, no new column, no new permission**.

**MUST NOT change (hard boundaries):**
- `baseline_physics_validation.py` rules, bounds, classifications, smoke test, `POLICY_VERSION`/contract.
- `expected_service` physics/math, `_expected_power_breakdown`, `REQUIRED_PHYSICS_FIELDS`.
- `crud.approve` / `crud.activate` gate logic, supersede behavior, `active_from`/`active_to`, single-active index.
- Lifecycle status machine, the structured-409 contract, `BaselineActivateRequest`.
- Authorization (Phase 0): `enforce_baseline_lifecycle_authority`, `telemetry_admin_required`, `get_authorized_site`.
- Read-path suppression semantics (`baseline_invalid`, NULL-never-0), period-effective stitching.
- Weather declaration / WS.5, device mapping, migrations, DB mutations beyond the optional additive audit row, historical expected, and **anything operational on Site 4**.

---

## 17. Browser validation strategy (for the eventual implementation)

- **Workflows:** Backend (uvicorn :8000), Frontend (:5000); drive via `$REPLIT_DEV_DOMAIN`.
- **Site 4 / 110 Shawmut — READ-ONLY:** confirm the grouped panel, field highlighting, source-basis labels, evidence links, readiness summary, and history all render against #4 (active, −0.35) and the suppressed #3 (invalid). Confirm the O&M expected chart still shows the −0.35 active curve and #3 stays suppressed (no corrupt curve). **Never approve/activate on Site 4.**
- **Forbidden path:** as a telemetry-admin **without** company-admin, confirm approve/activate render read-only (`lifecycle-readonly-explanation`) and the direct POSTs return the structured 403 — verify in the Network panel; re-read `list` to confirm #3/#4 status/points/validation JSON unchanged (no side effects).
- **Lifecycle happy-path:** on a **throwaway** test site only — create draft, preview, approve, then activate clean / warning-with-note / `hard_invalid`-blocked, asserting the grouped panel + acknowledgement UX behave and that a `hard_invalid` can never be waived.
- **Isolation:** the new presentation reads only the target baseline's own verdict; a draft's verdict never leaks into the public `expected-preview` (still 409s a draft `baseline_id`).
- **Automated:** extend the existing jest panel tests with grouped-severity, field-highlight-from-`fields[]`, source-basis, and history assertions; extend backend tests only if a read-only history endpoint is added.

---

## 18. Open product decisions

1. **Required reviewer notes beyond warning activation?** Should approval (or baseline-driving overrides) require a rationale note? (B2.8 — needs sign-off before changing the approve contract.)
2. **Discrete lifecycle audit log?** Add a best-effort `audit_logs` entry (existing table) on approve/activate so attribution/waivers are queryable, instead of JSONB-only? (B2.10 / §9.)
3. **Validation-history surface depth.** Show full per-version verdict history + waiver trail, or just current + immediate prior? Add a read-only history endpoint or reuse list/active?
4. **`in_review` / `rejected` statuses.** They exist in the enum but have no transition. Should B2 surface a "needs review" state mapped from readiness, or leave the enum dormant? (Display-only mapping recommended; no new transition.)
5. **Severity vocabulary surface.** Confirm the eight explicit states are the canonical set to standardize on across the tab.
6. **Evidence-link target.** Deep-link to the Data Room document page/snippet vs. a general document view — confirm the desired granularity.

---

## Return-only summary

1. **Audit findings:** §§1–13 — a mature, pure, fail-closed validation engine with a thin reviewer UI; one write point (activation stamps the verdict), everything else read-only; `hard_invalid` is unwaivable, warnings waivable only with a recorded note; the gaps are presentational (grouping, highlighting, evidence, source-basis, readiness summary, history).
2. **Recommended implementation plan:** §14 (B2.1–B2.10, sequenced) — additive display + intent-capture layer; one optional read-only/audit addition pending product approval.
3. **Affected files (for the eventual build):** frontend Reconciliation components + `telemetryV2.ts`/`telemetryV2` types (display); optionally one additive read-only endpoint in `app/routers/telemetry/v2.py` + a best-effort call to existing `app/helpers/telemetry/audit.py`. **No** change to `baseline_physics_validation.py`, `expected_service.py`, `crud/telemetry_expected.py` gates, models, or migrations.
4. **Existing routes:** §8 (list, active, create, readiness-from-facts, create-draft-from-facts, diff, points-readiness, generate-design-points, approve, activate, expected-preview, draft-preview).
5. **Existing data models:** §9 (`TelemetryExpectedBaseline`, `TelemetryExpectedBaselinePoint`, `TelemetryBaselineStatus/Type/Source`, `validation_result_json` shape).
6. **Existing frontend components:** §10 (Reconciliation, ReadinessSummary, BaselineFromFactsPanel, DraftBaselineReviewPanel, DraftPreviewOverlay, ReconciliationTable incl. its inline `StatusCell`).
7. **Existing tests:** §12 (backend physics/readiness/lifecycle/period-effective/wiring; frontend panel/reconciliation/diagnostics).
8. **Browser validation approach:** §17 — Site 4 read-only (render/forbidden/isolation/unchanged); lifecycle happy-path on throwaway sites only; never approve/activate on Site 4.
9. **Mutation boundaries:** §16 — display + optional additive read-only/audit only; engine, math, lifecycle, permissions, migrations, weather/WS.5, device mapping, historical expected, and Site 4 operations are off-limits.
10. **Confirmation that no production code was changed:** This sprint produced **only** this audit document (`docs/baseline_warning_validation_ux_audit.md`). No backend, frontend, schema, migration, permission, lifecycle, physics, expected-model, weather, or Site 4 changes were made.
