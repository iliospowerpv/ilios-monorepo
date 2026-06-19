# Expected Baseline Draft Review & Activation UX — Audit & Design

> **Sprint type: AUDIT & DESIGN ONLY.** This document contains no production code, migrations,
> endpoint, UI, or data-model changes, and proposes none for this sprint. Every recommendation
> below is gated behind a *future, separately-approved* implementation sprint. Nothing here
> auto-activates, auto-approves, mutates `project_facts`/accepted values, silently normalizes,
> touches expected math / telemetry ingestion / `WeatherResolver` / device eligibility / SAFL,
> or reintroduces BigQuery / Firestore / legacy telemetry.

---

## 1. Executive Summary

### 1.1 The single most important finding

The backend baseline approval/activation machinery **already exists end-to-end** —
`draft → approved → active` (superseding the prior active) with provenance, a single-active
partial-unique index, and a `supersedes_baseline_id` lineage chain. What is missing is (a) the
**frontend** to review, preview, approve, and activate a draft, and (b) one **safety property**
that the data model was explicitly designed for but the read path never honors.

That safety property is the crux of this sprint:

> **O&M expected is read from the *single* current `active` baseline with NO effective-date
> filtering. Activating a new baseline therefore silently rewrites the expected line for ALL
> historical periods**, even though the schema carries `active_from` / `active_to` precisely so
> historical periods could keep the baseline that was active *at the time*.

So the activation UX cannot be designed as "a button that flips status to active." It must be
designed around the fact that, **with today's read path, activation is a retroactive,
whole-history rewrite of the comparative-performance story** — which directly violates the
durable platform invariant ("historical data must remain preserved and auditable; no silent
survival/rewrite across source changes").

### 1.2 What exists today (confirmed)

| Capability | Backend | Frontend |
| :-- | :-- | :-- |
| Readiness from facts | ✅ `GET .../expected-baseline/readiness-from-facts` | ✅ `ReadinessSummary` + `BaselineFromFactsPanel` |
| Create **draft** from facts + reviewer inputs + confirm-only normalization | ✅ `POST .../expected-baseline/create-draft-from-facts` | ✅ `BaselineFromFactsPanel` |
| List baselines / get active | ✅ `GET .../expected-baselines`, `.../active` | ❌ no client fn, no UI |
| **Approve** a draft | ✅ `POST /expected-baselines/{id}/approve` | ❌ none |
| **Activate** an approved baseline (supersede prior) | ✅ `POST /expected-baselines/{id}/activate` | ❌ none |
| Expected **preview** | ✅ `GET .../expected-preview` (refuses drafts) | ❌ no client fn, no UI |
| O&M expected reads active baseline | ✅ `expected_service` + `v2_chart_data._active_baseline` | ✅ existing O&M charts |
| Design-estimate points (separate track) | ✅ `points-readiness`, `generate-design-points` | ✅ separate tile in `ReadinessSummary` |

### 1.3 The four design problems to solve

1. **No review surface** — a reviewer cannot see *what a draft contains* (sources, reviewer
   inputs, normalizations, defaults, warnings) before committing it.
2. **No safe preview** — the preview endpoint refuses `draft` status, so a reviewer cannot see
   the resulting expected curve before approving.
3. **Activation = silent historical rewrite** — the highest-severity integrity gap.
4. **FE/BE permission mismatch** — approve/activate are *stricter* on the backend
   (company-admin) than the FE's `useTelemetryAdminPermission` gate implies.

### 1.4 Recommended shape of the solution (preview)

A **two-step, explicit, telemetry-admin + company-admin** flow inside the existing Project Hub
Reconciliation surface: **Review → Approve → Preview → Activate**, where activation shows a
hard impact statement about historical analytics, and where the *historical-rewrite* problem is
either (a) fixed first (Phase 6, period-effective read) or (b) shipped with activation gated and
a prominent, accurate warning until Phase 6 lands. **This is a user decision (see §12).**

---

## 2. Current Baseline Lifecycle Audit (Area A)

All paths below are in `backend/ilios-server`. Router file: `app/routers/telemetry/v2.py`.
CRUD: `app/crud/telemetry_expected.py`. Service: `app/services/telemetry/baseline_from_facts_service.py`.
Model: `app/models/telemetry_expected.py`. Calc: `app/services/telemetry/expected_service.py`.
O&M chart binding: `app/helpers/telemetry/v2_chart_data.py`.

### 2.1 The status ladder (model: `TelemetryBaselineStatus`)

`draft → in_review → approved → active → superseded` (+ `rejected`).

- **Wired transitions today:** `draft → approved` (approve), `approved → active` (activate),
  `active → superseded` (automatic, during another baseline's activation).
- **Latent / unused:** `in_review` and `rejected` exist in the enum but **no endpoint
  transitions a baseline into them**. This is relevant to §5 (a two-person review/approve split
  could use `in_review`; a "reject draft" action could use `rejected`).

### 2.2 Step-by-step lifecycle

| # | Step | Endpoint (method + path) | Router fn | Permission | Service/CRUD | Tables written | Tx | Audit/provenance |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | Readiness | `GET /v2/sites/{site_id}/expected-baseline/readiness-from-facts` | `expected_baseline_readiness_from_facts` (~L2782) | `telemetry_admin_required` | `baseline_from_facts_service.evaluate_readiness` | none (read-only) | n/a | n/a |
| 2 | Create draft | `POST /v2/sites/{site_id}/expected-baseline/create-draft-from-facts` (~L2817) | `create_expected_baseline_draft_from_facts` | `telemetry_admin_required` | `create_draft_from_facts` → `CRUD.create_draft` | `telemetry_expected_baselines` (1 row, status `draft`) | single `commit()` in CRUD | `model_parameters_json` = `field_sources` map + `source_fact_ids` + `source_document_ids` + `source_fact_signature` + per-field AI confidence; `source_project_fact_id`, `source_document_id` columns |
| 3 | Inspect (list) | `GET /v2/sites/{site_id}/expected-baselines` (~L2639) | `list_expected_baselines` | `get_authorized_site` (asset view) | `CRUD.list_for_site` | none | n/a | returns all statuses, newest first |
| 3b | Inspect (active) | `GET /v2/sites/{site_id}/expected-baselines/active` (~L2656) | `get_active_expected_baseline` | `get_authorized_site` | `CRUD.get_active` | none | n/a | single active or `null` |
| 4 | Approve | `POST /v2/expected-baselines/{baseline_id}/approve` (~L3094) | `approve_expected_baseline` | `telemetry_admin_required` + `get_authorized_site_with_company_admin` + `_enforce_company_visibility` | `CRUD.approve` (L198) | same row: `status=approved`, `reviewed_by`, `approved_by`, `approved_at` | single `commit()` | sets `reviewed_by`/`approved_by` = actor |
| 5 | Activate | `POST /v2/expected-baselines/{baseline_id}/activate` (~L3128) | `activate_expected_baseline` (L3133) | `telemetry_admin_required` + `get_authorized_site_with_company_admin` + `_enforce_company_visibility` | `CRUD.activate` (L221) | **prior** active row: `status=superseded`, `active_to=now`; **this** row: `status=active`, `active_from=now`, `supersedes_baseline_id=prior.id` | single `commit()` w/ `FOR UPDATE` lock on prior | structured log line w/ supersede id |
| 6 | Preview | `GET /v2/sites/{site_id}/expected-preview` (~L3163) | `get_expected_preview` | `get_authorized_site` | `expected_service.compute_site_expected` | none | n/a | optional `baseline_id`; **refuses non-previewable statuses** |
| 7 | O&M read | (O&M chart endpoints) | `v2_chart_data._active_baseline` (L64) | (chart auth) | `CRUD.get_active` → `compute_site_expected` | none | n/a | **no effective-date filter** (see §4) |
| — | Legacy SAFL create | `POST /v2/sites/{site_id}/expected-baselines` (~L2671) | `create_expected_baseline` | `telemetry_admin_required` | `CRUD.create_draft` | `telemetry_expected_baselines` | commit | **deprecated**, logs steering warning |
| — | Design points | `.../expected-baseline/{id}/points-readiness`, `.../generate-design-points` | (design-points fns) | telemetry_admin | `baseline_points_service` | `telemetry_expected_baseline_points` | commit | **`design_estimate` only** (see §9) |

### 2.3 Models (`app/models/telemetry_expected.py`)

**`TelemetryExpectedBaseline`** (header — the immutable physics snapshot):

- Identity/scope: `id`, `company_id` (FK, CASCADE), `site_id` (FK, CASCADE), `baseline_name`,
  `baseline_type` (`design_estimate | weather_adjusted_model | imported_8760 | manual`),
  `status`, `source_type`.
- Provenance: `source_document_id` (FK SET NULL), `source_project_fact_id` (FK SET NULL),
  `model_parameters_json` (JSONB — field sources, fact-id list, `source_fact_signature`,
  AI confidence), `loss_assumptions_json`, `ai_confidence_json`, `notes`, `version`.
- Typed physics snapshot (calc reads ONLY these, never live `site_additional_fields`):
  `module_wattage`, `module_quantity`, `inverter_wattage`, `inverter_quantity`,
  `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`,
  `annual_degradation_pct`, `cec_efficiency_pct`, `soiling_factor`, `dc_loss_pct`, `ac_loss_pct`,
  `medium_voltage_loss_pct`, `mv_line_loss_pct`, `pto_date`, `timezone` (site-local age),
  `system_size_ac_kw`, `system_size_dc_kw`, `degradation_rate`.
- Lifecycle/attribution: `created_by_user_id`, `created_at`, `updated_at`, `reviewed_by`,
  `reviewed_at`, `approved_by`, `approved_at`, **`active_from`**, **`active_to`**,
  **`supersedes_baseline_id`** (self-FK SET NULL).
- Constraints: partial unique index `uq_telemetry_expected_baseline_active`
  `(site_id, baseline_type) WHERE status='active'` → at most one active per site+type.

**`TelemetryExpectedBaselinePoint`** (stored curve — primarily for `design_estimate`; the
weather-adjusted model is computed on read, not stored): `baseline_id`, `site_id`, `device_id`
(reserved), `point_ts`, `interval_minutes`, `expected_power_kw`, `expected_energy_kwh`,
`irradiance_wm2`, `cell_temperature_f`, `ambient_temperature_f`,
`source_granularity` (`hourly|daily|monthly|annual|interval`), `calculation_method`. Unique on
`(baseline_id, source_granularity, point_ts)`.

### 2.4 Audit findings from the lifecycle

- **F-A1 (positive):** The full server-side ladder exists, is provenance-rich, transactional,
  and preserves superseded rows for audit. Activation is a single locked transaction.
- **F-A2 (attribution gap):** `CRUD.activate(baseline, *, user_id=...)` accepts an actor, but
  **there is no `activated_by` / `activated_at` column** — activation persists only `active_from`
  (a timestamp) and the actor appears only in the log line. Approve, by contrast, persists
  `reviewed_by` + `approved_by`. *Who activated* is not durably recorded on the row.
- **F-A3 (no single-baseline detail endpoint):** There is `list` and `active`, but no
  `GET /expected-baselines/{id}`. A review screen for one draft must use `list` + client filter
  (acceptable) or a new detail endpoint (cleaner).
- **F-A4 (latent statuses):** `in_review` and `rejected` are modeled but unreachable — a future
  role-split or reject action can adopt them without a migration.
- **F-A5 (effective-date columns unused on read):** `active_from`/`active_to` are written on
  activation/supersession but **never read** — see §4.

---

## 3. Draft Baseline Review Requirements (Area B)

A reviewer must be able to answer "**is this draft correct, complete, and honest?**" *before*
approving — and "**what will activating it do?**" before activating. The review surface must
render, for the selected draft:

**Identity & status**
- `baseline_name`, `baseline_type` (must read "Weather-adjusted model"), `status` chip
  (`draft`), `created_by`, `created_at`, `version`, `supersedes_baseline_id` (if re-draft).

**Provenance & inputs (preserve every lineage distinction — never collapse them):**

| Layer (must stay visually distinct) | Source in the draft |
| :-- | :-- |
| Raw source value (e.g. `"340 Wp"`, `"66 kWac"`) | `model_parameters_json.field_sources[*].raw_value` |
| Accepted / promoted `project_fact` | `source_project_fact_id` + `field_sources[*].fact_id` |
| Reviewer-confirmed **normalized** value (raw→numeric) | `field_sources[*]` method/from→to + `confirmed_by`/`at` |
| Reviewer-supplied constant (5 physics constants) | typed columns + `field_sources` origin = reviewer |
| Optional **default** applied (loss 0%, soiling 1.0) | flagged as *default*, **not** a fact |

- For each driving field: **a chip stating its origin** (From facts / Normalized / Reviewer /
  Default), the value used, and a link to the source document (`source_document_id`) and the
  source fact id. **Normalized values must show both** the raw string and the numeric result,
  with the confirming user — never silently presented as if extracted.

**Warnings & honesty signals**
- Missing / low-confidence inputs (per-field AI confidence from `ai_confidence_json`).
- **PTO / pre-PTO behavior**: explicit statement that expected is `NULL` before `pto_date`
  (and that a missing `pto_date` suppresses the *entire* expected curve — carried from the
  readiness audit). PTO is a *warning*, not a draft blocker.
- Optional-defaults summary ("3 optional losses defaulted to 0%; soiling defaulted to 1.0").
- `model_parameters_json` human-readable summary (the field-sources table is the summary).

**Decision aids**
- **Expected calculation preview** (see §6) — the resulting curve vs actual.
- **Weather source / provenance readiness** — whether `WeatherResolver` can supply
  irradiance + cell temperature for the preview window (read-only; W1 semantics, never promote
  `unknown`→POA/cell).
- **Design-estimate points readiness — clearly separate** (X/12 months), with copy stating it
  is a *different* baseline and is **not** affected by activating this one (see §9).
- **Impact statement** (verbatim intent): *"Activation affects expected / comparative
  performance going forward, subject to the baseline's effective date."* — and, until Phase 6
  lands, an accurate stronger warning that activation will also recompute historical expected
  (see §4 / §12).

**F-B1:** The data to render all of the above already lives on the draft row + `model_parameters_json`.
No new *capture* is needed; the gap is purely *surfacing* (response shaping + UI).

---

## 4. Activation Safety & Historical Integrity Audit (Area C)

### 4.1 What activation does today

`CRUD.activate` (L221): locks the prior active row `FOR UPDATE`, sets it `superseded` +
`active_to=now`, sets the new row `active` + `active_from=now` +
`supersedes_baseline_id=prior.id`, single commit. The prior baseline **is preserved** (audit
intact). Activation requires `status==approved` (else 409). Effective date is **always `now`**;
**no backdating** is possible; **no `activated_by`** is persisted (F-A2).

### 4.2 How O&M reads expected

`v2_chart_data._active_baseline` (L64) → `CRUD.get_active(site_id, weather_adjusted_model)`
(L96) selects **the one row with `status=='active'`**, filtering by `site_id` + `baseline_type`
**only**:

```python
# app/crud/telemetry_expected.py
def get_active(self, site_id, baseline_type=weather_adjusted_model):
    return (q.filter(site_id==…, baseline_type==…, status==active).one_or_none())
```

There is **no comparison of the chart's query window against `active_from`/`active_to`**.
`compute_site_expected` then computes the curve from that baseline's immutable snapshot for the
*entire requested window*, regardless of when that window occurred.

### 4.3 The integrity gap (highest severity)

- **F-C1 (silent historical rewrite):** Activating baseline *B* (superseding *A*) makes **every**
  O&M expected line — including periods that occurred while *A* was the only active baseline —
  recompute against *B*'s parameters. The actual-vs-expected, losses, and performance-index
  history all change retroactively with no record on the chart that the comparison basis moved.
  This violates the durable invariant ("no silent survival/rewrite across source changes;
  historical data must remain preserved and auditable").
- **F-C2 (the schema already anticipated the fix):** The model docstring states *"Historical
  periods live in superseded rows (active_from / active_to)"* and the columns + `supersedes_baseline_id`
  chain exist. **Only the read selection is wrong** — it ignores the very columns designed to
  make history stable. The fix is therefore additive on the read path, not a schema change.
- **F-C3 (no effective-date control in the UX):** Because activation is always `now` and reads
  ignore dates, there is currently no honest way to say "this baseline applies from date X" —
  the UX has nothing to show or pick.

### 4.4 Honest computation behavior (positive)

`expected_service` never fabricates zeros: pre-PTO → `pre_pto` + `None`; missing irradiance/cell
temp → `missing_inputs` + `None`; no active baseline → `baseline_not_available`. The chart helper
fills *actual*/*irradiance* with `0.0` to satisfy the schema but **preserves `None` for
expected**. This honesty must be preserved by any preview/activation UX (§6).

### 4.5 Designed safe activation behavior

1. **Explicit two-step confirmation** (approve, then activate) — never one silent flip.
2. **Effective-date display** (and, optionally later, selection): show `active_from` and the
   superseded baseline's `active_to`. Backdating is **out of scope** until Phase 6.
3. **Hard warning about historical analytics** — until Phase 6 (period-effective read) lands,
   the activation dialog must state that **historical expected will be recomputed**, because
   that is the literal current behavior. After Phase 6, the warning softens to "affects periods
   from the effective date forward."
4. **No silent historical rewrite is acceptable as a permanent state** — Phase 6 makes the read
   window-aware so superseded baselines keep their periods. Any *intentional* recomputation
   (backfill) must be a **separate, explicit, period-scoped, audited** action — never a
   side effect of activation.
5. **Preserve the prior active row** (already true) and record `activated_by`/`activated_at`
   (close F-A2).

---

## 5. User-Facing Activation UX Design (Area D)

### 5.1 Where it lives

Inside the **existing Project Hub Reconciliation tab** (`…/tabs/Reconciliation/`), as a new
**Draft Baseline Review** surface reachable from `ReadinessSummary` (which already shows the
"Draft baseline" and "Active baseline" tiles). **No new standalone page, no orphaned route** —
consistent with prior O&M/PH rebinding decisions.

### 5.2 The flow

1. **Draft created** (existing `BaselineFromFactsPanel`) → success alert already says "not
   active, review/activate separately."
2. **Open Draft Baseline Review** (new) — renders §3's provenance/inputs/warnings table.
3. **Expected preview** (new, §6) — curve vs actual, honest unavailable states.
4. **Approve** (existing `POST …/approve`) — explicit confirm; stamps reviewer/approver; moves
   `draft → approved`.
5. **Activate** (existing `POST …/activate`) — **separate** explicit confirm with the impact
   statement + historical warning; supersedes prior active.
6. **Active state integration** — O&M now has an expected line; surface "Expected driven by
   baseline #X (active since …)" (§8).

### 5.3 Approval vs activation — recommendation

- **Two separate actions, not one combined confirm.** Approval = "the inputs are correct";
  activation = "make this the live comparison basis (and, today, rewrite history)." Collapsing
  them hides the most dangerous step. The backend already enforces `approved` before `activate`.
- **Role/permission posture (recommended):**
  - *Create draft / approve*: **telemetry-admin** (matches backend; create-draft is telemetry-admin).
  - *Activate / supersede*: **telemetry-admin AND company-admin** — this already matches the
    backend's `get_authorized_site_with_company_admin` on activate (and approve). Activation is
    the consequential, history-affecting step, so the stricter gate is appropriate.
  - **Optional two-person integrity (future):** use the latent `in_review` status so the drafter
    and approver can be different people (separation of duties). Not required for v1.
- **Effective date:** v1 shows `now` (read-only). Selectable/backdated effective dates wait for
  Phase 6, because they are meaningless until the read path is window-aware.

### 5.4 Anti-patterns to avoid

- No "Approve & Activate" single button.
- No activation without the historical-impact statement.
- No implying that activating the weather-adjusted baseline creates design-estimate points (§9).
- No fabricated expected values anywhere in the flow.

---

## 6. Expected Preview Design (Area E)

### 6.1 What exists & the blocker

`GET /v2/sites/{site_id}/expected-preview` (`get_expected_preview`, L3163) already computes a
preview via `compute_site_expected`, accepts an optional `baseline_id`, and otherwise defaults
to the active `weather_adjusted_model`. **But** `_PREVIEWABLE_BASELINE_STATUSES` =
`{approved, active, superseded}` — it returns 4xx ("Baseline must be approved before it can be
previewed") for a **`draft`**.

**F-E1:** A reviewer therefore **cannot see the expected curve of a draft before approving it** —
which is exactly the unsafe "approve blind" pattern. The preview is only usable *after* approval
(before activate) or for historical/audit of approved/active/superseded baselines.

### 6.2 Recommendation (design-only)

Two clean options for the future implementation sprint — **user to choose** (§12):

- **Option A — preview at the approved stage.** Keep `draft` non-previewable; the flow becomes
  Review (provenance only) → Approve → **Preview** → Activate. Lowest change, but the approver
  approves without seeing the curve.
- **Option B (recommended) — allow draft preview, read-only.** Extend the preview so a `draft`
  can be previewed (either add `draft` to the previewable set *for the review screen only*, or a
  dedicated draft-scoped preview path) while remaining **strictly read-only and persisting
  nothing**. This lets the reviewer see the curve *before* approving — the safest sequence. The
  preview must be unmistakably labeled "DRAFT PREVIEW — not active."

### 6.3 What the preview must render

- **Weather-adjusted expected** curve for a sensible window (e.g. last 30 days) from the draft's
  immutable snapshot.
- **Actual telemetry overlay** when available (V2 rollups) for visual comparison.
- **Honest unavailable states**, never fabricated: `pre_pto` (suppressed before PTO),
  `missing_inputs` (no irradiance/cell temp), `baseline_not_available`, missing-weather
  indication. Null expected renders as a gap / "N/A", **never 0**.
- **Labels for provenance-sensitive inputs**: which values are normalized, which are optional
  defaults — so the curve is never read as more authoritative than its inputs.
- **No design-estimate conflation** — the preview is the weather-adjusted model only; design
  points are a separate visual (§9).

---

## 7. Permission Model (Area F)

### 7.1 Backend gates (authoritative)

| Action | Gate |
| :-- | :-- |
| Readiness from facts | `telemetry_admin_required` |
| Create draft from facts | `telemetry_admin_required` |
| Legacy SAFL create | `telemetry_admin_required` |
| List / active / preview | `get_authorized_site` (asset view) |
| **Approve** | `telemetry_admin_required` **+ `get_authorized_site_with_company_admin` + company-visibility** |
| **Activate / supersede** | `telemetry_admin_required` **+ `get_authorized_site_with_company_admin` + company-visibility** |
| Design points | `telemetry_admin_required` |

### 7.2 Frontend gate

`src/hooks/useTelemetryAdminPermission.ts` → `true` if `is_system_user` OR `is_global_admin` OR
`role.permissions.Telemetry.admin` OR `role.permissions['Settings Page'].edit`. Today this gates
only **create-draft** (`Reconciliation.tsx` `canDraftBaseline`) and the Telemetry-tab schedule
controls. `Diligence.edit` separately gates Promote / Create-Task in the audit table.

### 7.3 Findings

- **F-F1 (FE/BE mismatch on approve/activate):** Approve and activate additionally require
  **company-admin** on the backend, but `useTelemetryAdminPermission` does **not** check
  company-admin. A telemetry-admin who is *not* a company-admin would see the buttons (if we
  reused that hook) but be **rejected with 403**. The FE must either (a) introduce a
  company-admin-aware gate for approve/activate, or (b) always render the action but handle 403
  gracefully with an explanatory message. **Recommend (a) for honesty, with (b) as the
  fail-safe.**
- **F-F2 (consistency):** The existing pattern (FE mirrors the backend gate; backend re-enforces)
  is good — keep approve/activate buttons gated by the *stricter* company-admin-aware predicate
  so the UI never offers an action the backend will reject.
- **F-F3 (no stale labels found):** create-draft's FE gate already matches its backend
  (`telemetry_admin`). The only gap is the *new* approve/activate surfaces.

---

## 8. Reconciliation & Baseline Readiness Integration (Area G)

`ReadinessSummary` already renders three tiles: **Draft baseline (weather-adjusted)**,
**Active baseline**, **Design-estimate points (X/12)**. The integration design extends these to
reflect the full lifecycle truth, read-only and honestly:

| State to reflect | Where | Source |
| :-- | :-- | :-- |
| Draft exists (and it uses active facts / reviewer constants / normalized values) | Draft tile → "Open review" | `list` baselines (status `draft`) + `model_parameters_json.field_sources` |
| Draft is ready / not ready | Draft tile (existing) | `readiness-from-facts` |
| Approved (awaiting activation) | new sub-state on Draft/Active tiles | `list` (status `approved`) |
| Active baseline exists (id, since when) | Active tile (existing, extend with `active_from`) | `get active` |
| **Active baseline is STALE** because promoted facts changed since it was built | new chip on Active tile + Reconciliation rows | compare `model_parameters_json.source_fact_signature` to current promoted facts (Phase 5) |
| Design-estimate points missing | Design tile (existing) | `points-readiness` |
| Expected ready / not ready (live) | Active tile + O&M | `expected-preview` / O&M `expected_state` |

- **F-G1 (staleness is the key new signal):** The platform invariant requires that upstream
  (project_fact) changes must not silently survive in a downstream active baseline. Today nothing
  tells a reviewer that the active baseline was built from now-superseded facts. A **read-only
  staleness indicator** (signature mismatch) is the Reconciliation/Readiness counterpart to the
  promotion freshness guard — it flags "re-review / re-draft," it does **not** auto-act.
- **F-G2:** O&M should show *which* baseline drives the current expected line and since when (§8
  table row "Active baseline exists"), turning the chart from anonymous into auditable.

---

## 9. Design-Estimate Separation (Area H)

Four distinct notions must remain visually and conceptually separate; the UX must never let a
user believe activating one creates another:

1. **Weather-adjusted expected baseline** (`weather_adjusted_model`) — the live O&M expected
   line, computed on read, driven by physics snapshot + measured weather. *This* is what the
   review/approve/activate flow operates on.
2. **Design-estimate baseline** (`design_estimate`) — the static PVsyst/contract forecast; a
   **different `baseline_type`**, with its **own** endpoints (`points-readiness`,
   `generate-design-points`) and **stored** monthly/annual points.
3. **Design-estimate monthly points** (`telemetry_expected_baseline_points`, X/12) — produced by
   `baseline_points_service`, shown in its own `ReadinessSummary` tile.
4. **Actual telemetry** — V2 rollups; the overlay, never the baseline.

- **F-H1:** Separation already holds structurally (distinct type, endpoints, storage, tile) and
  in O&M (`_active_baseline` is `weather_adjusted_model`-only; the weather-adjusted model stores
  **no** points). The design must *preserve* this — e.g. the activation dialog explicitly states
  "This does **not** create or change design-estimate points," and the preview never overlays
  design points onto the weather-adjusted curve.

---

## 10. Phased Implementation Plan (Area I)

> All phases are future, separately-approved sprints. Ordering reflects risk and dependency.

### Phase 1 — Draft Baseline Review panel (read-only)
- **Risk:** Low (read-only surfacing).
- **Backend:** likely a response-shaping change to expose `model_parameters_json` provenance
  cleanly (optionally a `GET /expected-baselines/{id}` detail endpoint — F-A3). No writes.
  Files: `app/routers/telemetry/v2.py`, `app/schema/telemetry_v2.py`.
- **Frontend:** new `DraftBaselineReview` component under `…/tabs/Reconciliation/components/`;
  `telemetryV2.ts` `listBaselines`/`getBaseline`; wire from `ReadinessSummary`.
- **Tests:** review shows fact sources, reviewer values, normalized raw→numeric, optional
  defaults *as defaults*, PTO warning.
- **Non-goals:** no approve/activate, no expected curve yet.

### Phase 2 — Activation confirmation + permission audit
- **Risk:** Medium (state transition; supersedes prior active; **with current read path this
  rewrites history** — see the Phase 6 gating decision in §12).
- **Backend:** none required to *function* (endpoints exist). **Recommended additive:**
  `activated_by`/`activated_at` columns + persist actor (close F-A2) — a nullable-only migration.
  Files: model + `app/crud/telemetry_expected.py` + migration.
- **Frontend:** approve + activate buttons with **two separate** confirm dialogs; impact +
  historical warning; company-admin-aware gate (F-F1); `approveBaseline`/`activateBaseline`
  clients; graceful 409/403 handling.
- **Tests:** activation requires explicit confirm; prior preserved + superseded; **no
  `project_facts` mutated**; **no accepted values mutated**; permission enforced (telemetry-admin
  + company-admin); 409 when not approved.
- **Non-goals:** no period-effective read; no backdating; no auto-activate.

### Phase 3 — Expected preview before activation
- **Risk:** Medium (compute path; must stay honest).
- **Backend:** enable preview for the review screen — Option A (approved-stage only, no change)
  or Option B (draft preview, read-only, persists nothing) per §6/§12. Files:
  `app/routers/telemetry/v2.py` (`_PREVIEWABLE_BASELINE_STATUSES` / a draft-preview path),
  reuse `expected_service` unchanged.
- **Frontend:** preview chart in the review panel via `getExpectedPreview(baseline_id)`; actual
  overlay; honest `pre_pto`/`missing_inputs`/`baseline_not_available` states.
- **Tests:** preview shows expected vs actual; pre-PTO suppression; missing-weather indication;
  **no fabricated zeros**; draft preview persists nothing; no design-point conflation.
- **Non-goals:** no expected-math change; no design points.

### Phase 4 — Active baseline status integration into O&M
- **Risk:** Low–Medium.
- **Backend:** additively expose the driving baseline id + `active_from` on O&M chart responses
  (no compute change). Files: O&M routers/`v2_chart_data.py` schema.
- **Frontend:** O&M caption "Expected driven by baseline #X (active since …)" + deep link to the
  review surface.
- **Tests:** O&M expected uses the active baseline after activation; caption reflects the active id.
- **Non-goals:** no recompute behavior change.

### Phase 5 — Stale-baseline indicators when source facts change
- **Risk:** Medium (read-only detection).
- **Backend:** a read-only staleness check comparing the active baseline's
  `source_fact_signature` against current promoted facts (conceptually mirrors the promotion
  freshness guard). Files: a small service + readiness/reconciliation response fields.
- **Frontend:** stale chip on the Active tile + affected Reconciliation rows ("re-review").
- **Tests:** stale detected on fact change; no auto-action; signature match ⇒ not stale.
- **Non-goals:** no auto-supersede; no mutation of facts/baselines.

### Phase 6 — Historical period-effective baseline selection (the integrity fix)
- **Risk:** **High** — changes which baseline drives historical expected; the most sensitive
  change in the program. Must be carefully tested and, ideally, feature-flagged.
- **Backend:** make `expected_service` / `_active_baseline` **window-aware** — select the
  baseline whose `[active_from, active_to)` covers each bucket (walking the `supersedes_baseline_id`
  chain), instead of always the current active. Files: `app/helpers/telemetry/v2_chart_data.py`,
  `app/crud/telemetry_expected.py`, `app/services/telemetry/expected_service.py`.
- **Frontend:** minimal (charts already render per-bucket); the activation warning softens to
  "affects periods from the effective date forward"; effective-date selection can now be exposed.
- **Tests:** historical periods keep the baseline active at the time; activation no longer
  rewrites history; a window with no covering baseline flags a gap (honest `baseline_not_available`),
  never silently 0; backfill (if ever added) is separate/explicit/period-scoped/audited.
- **Non-goals:** no automatic backfill recompute; no change to the physics formula.

### Phase 7 — Design-estimate points flow (later, separate track)
- **Risk:** Low.
- **Scope:** formalize the existing `design_estimate` points endpoints into their own clearly
  separated UI track; never coupled to weather-adjusted activation.
- **Non-goals:** never conflate with the weather-adjusted baseline lifecycle.

---

## 11. Test Plan (Area J)

Design (not implement) the following. Backend tests live under
`backend/ilios-server/tests/unit/telemetry/`; FE under the component's `__tests__`.

**Review surface**
1. Draft review shows each driving field's `project_fact` source (id + document link).
2. Draft review shows reviewer-supplied constants distinctly from facts.
3. Draft review shows normalized raw→numeric values (both raw string and numeric) with confirmer.
4. Optional defaults render *as defaults*, never as facts.
5. PTO warning appears (and the "missing PTO suppresses whole curve" note).

**Activation safety**
6. Activation requires explicit confirmation (no single combined approve+activate).
7. Activating supersedes the prior active baseline **and preserves it** (`superseded` + `active_to`).
8. **No `project_facts` are mutated during approve or activate.**
9. **No accepted values are mutated during approve or activate.**
10. O&M expected uses the active baseline after activation (Phase 4 caption reflects id).
11. **Historical expected** — assert one of: (a) Phase 6 present → historical periods are *not*
    rewritten (each period keeps its at-the-time baseline); or (b) Phase 6 absent → the test
    documents that current behavior rewrites history **and** the activation UX surfaces that
    warning (so the gap is flagged, never silent).

**Permissions**
12. Approve/activate enforced for telemetry-admin **+ company-admin**; a telemetry-admin who is
    not company-admin is rejected (403) and the FE gate hides/disables the action (F-F1).
13. 409 returned when activating a non-`approved` baseline.

**Preview**
14. Preview shows expected vs actual; `pre_pto`/`missing_inputs`/`baseline_not_available` render
    as honest gaps, never 0; draft preview (if Option B) persists nothing.

**Invariants / non-regression**
15. **No SAFL** is used as a baseline source anywhere in the flow.
16. **No BigQuery / Firestore / legacy** path is touched.
17. Staleness (Phase 5) detects fact changes without mutating anything.
18. Design-estimate points are unaffected by weather-adjusted activation (§9).
19. **Architect review** of each phase before merge.

---

## 12. Open Questions for the User

1. **Historical-rewrite gating (most important).** Today, activation rewrites all historical
   expected (F-C1). Do you want to: **(a)** require Phase 6 (period-effective read) to land
   *before* any activation UI ships; or **(b)** ship activation earlier with a prominent,
   accurate "this will recompute historical expected" warning and fix history in Phase 6? This is
   a product-risk call.
2. **Preview point (§6).** Option A (preview only after approval) or Option B (recommended:
   read-only **draft** preview so the approver sees the curve before approving)?
3. **Approval vs activation split.** Confirm two separate actions (recommended). Do you also want
   true **separation of duties** (different drafter vs approver, using the latent `in_review`
   status), or is single-admin acceptable for v1?
4. **Activation permission.** The backend currently requires **company-admin** for approve +
   activate. Keep that (recommended), or relax activate to telemetry-admin only? (Affects F-F1.)
5. **Effective date.** v1 shows `now` only (no backdating). Confirm backdating/selectable
   effective dates are deferred to Phase 6.
6. **Attribution.** OK to add nullable `activated_by`/`activated_at` columns (Phase 2) to close
   the activation attribution gap (F-A2)?
7. **Reject action.** Do you want a "reject draft" action (using the latent `rejected` status),
   or is deleting/superseding-by-redraft sufficient?
8. **Staleness scope (Phase 5).** Should a stale active baseline (source facts changed) merely be
   *flagged* (recommended), or also *block* something (e.g. warn in O&M)? It must never
   auto-act.
9. **Surface placement.** Confirm the review/activation UX belongs in the **Reconciliation tab**
   (recommended, reuses `ReadinessSummary`) rather than the Telemetry tab.

---

### Appendix — Primary source references

- Router: `backend/ilios-server/app/routers/telemetry/v2.py` (list ~L2639, active ~L2656,
  legacy create ~L2671, readiness-from-facts ~L2782, create-draft-from-facts ~L2817,
  approve ~L3094, activate ~L3128/3133, preview ~L3163, `_PREVIEWABLE_BASELINE_STATUSES` ~L2629).
- CRUD: `backend/ilios-server/app/crud/telemetry_expected.py` (`get_active` L96, `approve` L198,
  `activate` L221).
- Service: `backend/ilios-server/app/services/telemetry/baseline_from_facts_service.py`
  (`create_draft_from_facts`, `evaluate_readiness`).
- Calc: `backend/ilios-server/app/services/telemetry/expected_service.py` (`compute_site_expected`,
  honest `None` states).
- O&M binding: `backend/ilios-server/app/helpers/telemetry/v2_chart_data.py` (`_active_baseline`
  L64 — no effective-date filter).
- Model: `backend/ilios-server/app/models/telemetry_expected.py` (`TelemetryExpectedBaseline`,
  `TelemetryExpectedBaselinePoint`, status/type enums, partial-unique active index).
- Frontend: `frontend/rea-investment-fe/src/modules/project-hub/pages/AssetManagementSiteDetails/tabs/Reconciliation/`
  (`Reconciliation.tsx`, `components/ReadinessSummary.tsx`, `components/BaselineFromFactsPanel.tsx`),
  `…/tabs/Telemetry/Telemetry.tsx`, `src/api/telemetryV2.ts`, `src/types/telemetryV2.ts`,
  `src/hooks/useTelemetryAdminPermission.ts`.
- Related prior audits: `docs/expected_baseline_readiness_input_audit.md`,
  `docs/promote_from_reconciliation_audit.md`, `docs/om_v2_alignment_audit.md`.
