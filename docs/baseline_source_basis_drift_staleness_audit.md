# Baseline Source-Basis Drift / Staleness — Audit & Design (Phase B4)

**Status:** Audit / design sprint only. No production code was changed. No
migrations were run. No Site 4 data was mutated. The sole deliverable is this
document.

**Scope question:** How does iliOS detect and display when an *active* expected
baseline's **source basis** (the promoted `project_facts` / documents it was
built from) has changed since approval/activation — **without** automatically
changing expected output or baseline status?

**Governance (non-negotiable for any future implementation):**

- An active baseline stays active until a human explicitly changes it.
- Source-basis drift is **informational / needs-review only**.
- No automatic deactivation, recalculation, baseline-math change, historical
  expected rewrite, or silent fact promotion / source replacement.

---

## 0. TL;DR

1. **Basis snapshots already exist — partially.** The facts→baseline bridge
   (`baseline_from_facts_service.py`) stamps a per-field source snapshot into
   `model_parameters_json` (`source_facts[]`, `field_sources{}`,
   `source_fact_signature`) plus header pointers (`source_project_fact_id`,
   `source_document_id`). This covers **only the four fact-backed physics
   fields** (module/inverter wattage + quantity). The five reviewer-supplied
   datasheet constants, the loss fields, and PTO have **no fact lineage** in the
   snapshot.

2. **Active-baseline drift detection already exists — partially, and it is
   read-only.** `reconciliation_service.build_site_reconciliation` emits a
   `W_ACTIVE_OUTDATED` ("active_baseline_outdated") warning per header field and
   maps it to `blocking_level = blocks_reporting` plus the action *"Rebuild the
   active baseline to include the latest promoted value."* It never deactivates,
   recomputes, or promotes anything. This satisfies the governance posture.

3. **The detection is weak in several concrete ways** (the central gaps):
   - It is **value-insensitive**: it keys on fact-**id membership** and a
     coarse **timestamp** (`fact_time > baseline.created_at`), *not* on whether
     the value actually changed. A re-promotion to the *same* value with a new
     `fact_id` (or a later timestamp) is flagged as drift even though nothing
     material changed (false positive).
   - It only covers the **four fact-backed fields**. Drift in the five
     reviewer-supplied physics constants (e.g. `thermal_coefficient_pct`) is
     never evaluated.
   - Baselines created **outside the bridge** do not **automatically** carry
     the bridge basis snapshot (nothing structurally prevents a manually
     populated `model_parameters_json`, but the bridge fields are absent by
     default), so they look permanently "outdated."
   - Unit-bearing fact values (e.g. `"340 Wp"`) cannot be compared by the plain
     `_coerce_number` helper (it returns `None` for them); a value-based
     comparator must normalize units explicitly.

4. **Site 4 is a live example of the gaps.** Active baseline **#4** was created
   by a manual "replacement/correction" path (to fix #3's invalid
   `thermal_coefficient_pct = 350.0` → `-0.35`). It has a human-authored
   `replacement` provenance blob but **no `source_facts`, no signature, and a
   NULL `source_project_fact_id`**. Its physics values exactly match the current
   active facts, yet today's detection would flag **all four** fact-backed
   fields as `active_baseline_outdated` purely because the snapshot is empty.

5. **Recommended direction:** add a **read-only, on-read** *source-basis drift*
   computation that compares the active baseline's **recorded basis** (snapshot
   values + signature) against the **current promoted facts by value**, classify
   the result into explicit states (including a distinct `basis_unknown` for
   non-bridge baselines so they are not falsely flagged), and surface it at the
   **baseline level** (history panel + readiness summary), not just per field.
   No migration is required for the recommended phase.

---

## 1. Audit findings

### 1.1 Promoted project facts (`project_facts`)

- Model: `app/models/project_facts.py` → `ProjectFact`.
- `status` is a plain string column over `FactStatus` = `candidate` / `active` /
  `retired`. Exactly the `active` rows are the canonical promoted assumptions.
- `value` is `JSONB` using the **envelope** `{"v": <scalar>}`; the scalar is
  frequently a **string carrying units** (e.g. Site 4 `module_wattage` =
  `{"v": "340 Wp"}`, `inverter_wattage` = `{"v": "66 kWac"}`). Every consumer
  must `_unwrap` and coerce; non-numeric values are treated as missing, never
  guessed.
- Provenance / audit columns (all additive, mostly nullable): `source_file_id`,
  `source_run_id` (→ `ai_parsing_results`), `source_document_key_id`,
  `promoted_by_id` / `promoted_at` / `promotion_notes`, `accepted_by_id` /
  `accepted_at`, `overridden_by_id` / `overridden_at` / `override_notes`,
  `supersedes_fact_id` / `superseded_by_fact_id`, `ai_confidence`,
  `ai_extracted_value`, `evidence`, `effective_from` / `effective_to`,
  `source_document_type`.
- `assumptions_promotions` records each promotion event (`site_id`,
  `document_id`, `file_id`, `promoted_by_id`, `promoted_at`, `diff_json`) — an
  event log, not a per-fact basis store.

### 1.2 Baseline source basis / snapshots

- Model: `app/models/telemetry_expected.py` → `TelemetryExpectedBaseline`
  (header) + `TelemetryExpectedBaselinePoint` (curve points).
- The physics assumptions are **snapshot as immutable typed columns** at
  creation (`module_wattage`, `module_quantity`, `inverter_wattage`,
  `inverter_quantity`, `thermal_coefficient_pct`, `power_tolerance_min_pct`,
  `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct`,
  `soiling_factor`, `dc_loss_pct`, `ac_loss_pct`, `medium_voltage_loss_pct`,
  `mv_line_loss_pct`, `pto_date`). The calc service reads only this snapshot, so
  an approved baseline is reproducible. **The snapshot stores the *values*, not
  the *identity/version* of each contributing source.**
- `model_parameters_json` (set by the bridge) is the closest thing to a true
  source-basis record:
  - `source_fact_signature` — a SHA-256 over `{baseline_type, facts:
    {canonical_name: value}, reviewer: {non-null reviewer values}}`.
  - `field_sources{column → {source, fact_id, document_id, ai_confidence,
    [normalization]}}` — per-field provenance. `source` is one of
    `project_fact` / `project_fact_normalized` / `reviewer_supplied`.
  - `source_facts[]` — a list of `{canonical_name, column, fact_id, value,
    document_id, ai_confidence}` for each contributing fact.
- `ai_confidence_json` and `loss_assumptions_json` carry confidence + loss
  detail. `validation_result_json` / `validation_policy_version` carry the
  physics-validation verdict (see §1.5).

### 1.3 `source_document_id` and `source_project_fact_id` usage

- On the baseline header both are **nullable single FKs** (`SET NULL` on
  delete): `source_project_fact_id` → `project_facts.id`,
  `source_document_id` → `documents.id`.
- The bridge sets `source_project_fact_id` to the **primary** fact only
  (`module_wattage`); the *full* contributing set lives in
  `model_parameters_json['source_facts']`. `source_document_id` is set **only
  when all contributing facts resolve to exactly one document** — multi-document
  baselines leave it `NULL`.
- They are **provenance pointers, not a basis manifest**: a single FK cannot
  express "which fact produced each of the nine physics inputs."

### 1.4 Baseline approval & activation records

- Status lifecycle enum `TelemetryBaselineStatus`: `draft` → `in_review` →
  `approved` → `active` → `superseded` / `rejected`.
- Approval/activation fields on the header: `reviewed_by` / `reviewed_at`,
  `approved_by` / `approved_at`, `active_from` / `active_to`,
  `supersedes_baseline_id`, `version`, `created_by_user_id`, `created_at` /
  `updated_at`.
- A partial unique index (`uq_telemetry_expected_baseline_active`,
  `WHERE status = 'active'`) enforces **exactly one active baseline per
  (site, baseline_type)**. Activation supersedes the prior active row (sets its
  `active_to`); the active baseline is treated as **immutable** and is replaced
  via supersede, never edited in place.
- Lifecycle transitions (`approve`, `activate`, supersede + the physics gate)
  live in `app/crud/telemetry_expected.py`.

### 1.5 `validation_result_json`

- Written in `app/crud/telemetry_expected.py` `activate(...)`; shape from
  `BaselineValidationReport` (`app/services/telemetry/baseline_physics_validation.py`):
  `policy_version`, `is_blocking`, `fields[]` (per-column classification /
  reason / entered value), `smoke_test{}`, and an `activation{}` block added at
  write time (`acknowledged_warnings`, `source_note`, `activated_by_user_id`,
  `activated_at`).
- It is a **physics-validity** verdict, not a source-basis record. It says
  nothing about whether the source facts have changed since activation, and is
  **not** part of the baseline-list response.

### 1.6 Reconciliation lineage

- Service: `app/services/due_diligence/reconciliation_service.py` →
  `build_site_reconciliation`. Strictly read-only (no writes/commits, never
  recomputes baselines; reads baselines/points verbatim).
- Per-field most-advanced-stage-wins status ladder: `in_active_baseline` >
  `in_draft_baseline` > `active_fact` > `accepted_not_promoted` >
  `candidate_only` > `accepted_document_value` > `ai_extracted_only` >
  `superseded` > `missing`.
- **This is where active-baseline drift is detected today** (see §1.8).

### 1.7 Current baseline history UI / ValidationHistoryPanel

- `ValidationHistoryPanel.tsx`
  (`frontend/rea-investment-fe/src/modules/project-hub/pages/AssetManagementSiteDetails/tabs/Reconciliation/components/`)
  consumes `ExpectedBaselineResponse[]` from
  `ApiClient.telemetryV2.listExpectedBaselines(siteId)` →
  `GET /api/telemetry/v2/sites/{site_id}/baselines`.
- It renders per baseline: status chip, `baseline_name (#id, vX)`, "Supersedes
  #ID", a lifecycle timeline (`Created / Approved / Active from / Active to`),
  and a summary of build-time warnings from `model_parameters_json`.
- It does **not** render the waiver trail (not carried on the list response) and
  has **no source-basis-drift indicator** at the baseline level. The only drift
  surface today is the per-field Reconciliation table (`StatusCell`) +
  `ReadinessSummary`.

### 1.8 Existing stale / needs-review states

Reconciliation warnings (orthogonal to status):

| Constant | Value | Meaning |
| --- | --- | --- |
| `W_MISSING_REQUIRED` | `missing_required_for_baseline` | Required value absent everywhere |
| `W_FACT_VS_LEGACY` | `fact_differs_from_legacy` | Promoted fact ≠ legacy SAFL (display-only) |
| `W_DRAFT_VS_ACTIVE` | `draft_differs_from_active` | Draft baseline value ≠ active baseline value |
| `W_ACTIVE_OUTDATED` | `active_baseline_outdated` | **Active-baseline source-basis drift** |
| `W_DESIGN_POINTS_MISSING` | design points absent | Design curve gap |
| `W_NEEDS_REVIEW` | genuine conflict | Human-resolution conflict |

**`W_ACTIVE_OUTDATED` is the only existing active-baseline drift signal.** Its
logic (`_build_row`, with inputs assembled in `_Ctx`):

- `_baseline_source_fact_ids(baseline)` = the set of `fact_id`s in
  `model_parameters_json['source_facts']` **∪** `baseline.source_project_fact_id`.
- `ctx.wam_active` = active `weather_adjusted_model` baseline;
  `ctx.wam_active_fact_ids` = that set; `ctx.wam_active_created` = the baseline's
  `created_at` (as naive-UTC).
- For a `HEADER_COLUMN` baseline-driving field with an `active_fact` and a
  present active baseline, drift fires when:
  `active_fact.id not in wam_active_fact_ids` **OR**
  (`_fact_time(active_fact) > wam_active_created`).
- It maps to `blocking_level = blocks_reporting` and, when the field's status is
  `in_active_baseline`, to the action *"Rebuild the active baseline to include
  the latest promoted value."* The readiness block additionally returns
  `active_baseline_available` / `active_baseline_id` / `active_baseline_created_at`.

**Related but different — the promotion freshness guard.**
`app/services/promotion_service.py` `validate_promotion_freshness` is a
fail-closed, all-or-nothing **pre-promotion** check (HTTP 409
`PROMOTION_SOURCE_STALE`) comparing a candidate's `source_run_id` to the latest
completed parse run for the file version. It protects *promotion*; it does
**not** evaluate an already-active baseline against current facts.

### 1.9 Net conclusion

The platform already has the *foundations* of source-basis drift detection
(a snapshot in `model_parameters_json`, an `active_baseline_outdated` warning,
and a manual "rebuild" remediation path that respects governance). What is
missing is **accuracy** (value-based comparison vs. id/time heuristic),
**coverage** (reviewer-supplied physics constants; non-bridge baselines), and
**surfacing** (a baseline-level drift state, not just per-field rows).

---

## 2. Current data sources (what drift detection can read today)

| Source | Location | Carries |
| --- | --- | --- |
| Current promoted facts | `project_facts` (status `active`) | live values + provenance + `promoted_at` |
| Baseline typed snapshot | `telemetry_expected_baselines.*` columns | immutable physics values used by the calc |
| Baseline basis snapshot | `…model_parameters_json` (`source_facts`, `field_sources`, `source_fact_signature`) | the fact ids/values/docs the bridge used (4 fact-backed fields only) |
| Baseline header pointers | `source_project_fact_id`, `source_document_id` | single primary fact + single document (nullable) |
| Lifecycle timestamps | `created_at`, `approved_at`, `active_from`, `active_to` | when the basis was captured / went live |
| Promotion events | `assumptions_promotions` | when/what/who promoted (event log) |
| Reconciliation read model | `reconciliation_service` | already computes `active_baseline_outdated` |

Everything required for a **value-based** comparison of the active baseline's
basis vs. current promoted facts is already present **for the four fact-backed
fields**. The recorded `source_fact_signature` even encodes the values used, but
it is currently only used for *draft* dedupe, never recomputed against current
facts for an active baseline.

---

## 3. Do basis snapshots already exist?

**Yes — partially, and only for bridge-built baselines.**

- **Present:** `source_facts[]` (fact ids + values + doc ids) and
  `source_fact_signature` (hash over fact values ∪ reviewer values), plus the
  immutable typed-column value snapshot. This is enough to detect value drift
  for the four fact-backed fields.
- **Absent / weak:**
  - No snapshot for the **five reviewer-supplied required physics constants**
    (`thermal_coefficient_pct`, `power_tolerance_min_pct`,
    `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct`),
    the loss fields, or PTO — their `field_sources` entry is just
    `{"source": "reviewer_supplied"}` with no `fact_id`. There is no current
    "live reviewer value" to compare against, so these can change only via a new
    baseline, never via fact drift.
  - **No bridge snapshot by default** on baselines created outside the bridge
    (manual create, the legacy `create_draft`, or a correction/replacement
    path — see Site 4 #4). Nothing structurally prevents a manually populated
    `model_parameters_json`, but the bridge fields (`source_facts`,
    `source_fact_signature`) are absent unless the creator writes them; Site 4
    #4's `source_facts` is empty and `source_project_fact_id` is NULL.
  - The snapshot is keyed on **fact id**, not a stable **(field, value)** basis,
    so an equal re-promotion changes the id without changing the basis.
  - No persisted **drift state** (detected/acknowledged) — drift is recomputed
    on every reconciliation read (acceptable for governance, but there is no
    acknowledgement ledger like the inventory-reconciliation one).

---

## 4. Gaps — comparing active baseline basis to current promoted facts

| # | Gap | Effect today | Governance-safe target |
| --- | --- | --- | --- |
| G1 | **Value-insensitive comparison** (id membership + `fact_time > created_at`) | Equal re-promotion → false "outdated"; Site 4 is a live false positive | Compare by **value** (recompute signature over current active facts ∪ recorded reviewer values, or per-field value equality with unit-aware coercion) |
| G2 | **Coverage limited to 4 fact-backed fields** | Reviewer-supplied physics constants (e.g. thermal coeff) never drift-checked | Explicitly classify reviewer-only fields as `no_fact_lineage` (informational), never silently ignore |
| G3 | **No bridge basis snapshot by default on non-bridge baselines** | Such baselines look permanently outdated (Site 4 #4) | Distinct `basis_unknown` state, **not** drift |
| G1b | **Unit-bearing values defeat naive numeric coercion** (`_coerce_number("340 Wp") → None`) | A naive comparator would treat text-with-unit facts as missing and mis-flag | Reuse the bridge normalization (`input_norm.propose()` + confirmation) or a dedicated unit parser |
| G4 | **Timestamp anchor is `created_at`** (not `active_from`/`approved_at`) | A fact promoted between create and activate can flag drift | Anchor temporal comparison to activation (`active_from`/`approved_at`) and/or drop time in favor of value |
| G5 | **No baseline-level surfacing** | Drift only appears per-field in the Reconciliation table; the history panel/active-baseline card show nothing | Add a read-only baseline-level drift summary (badge + field list) |
| G6 | **Document-version drift not modeled** | New uploaded versions are seen only indirectly via fact-id change | Optionally compare `source_document_id`/version against the latest promoted document (informational) |
| G7 | **No acknowledgement / audit of drift** | Drift cannot be "reviewed and accepted as known" | (Optional, later) append-only drift acknowledgement, mirroring inventory recon — informational only |

**Central gap = G1 + G3.** The recorded `source_fact_signature` already encodes
the basis values; the system simply never recomputes it against current facts
for an active baseline, and it has no explicit "unknown basis" state — so it
substitutes an id/time proxy that produces false positives.

---

## 5. Recommended implementation plan (design only — not built)

A single read-only seam, layered so the cheap, no-migration phase delivers the
core value. Every phase preserves the governance rules (informational /
needs-review only; the **only** remediation remains the existing manual
"create + activate a new draft").

### Phase D1 — Canonical, read-only "source-basis drift" resolver (no migration)

- New pure function/service (e.g. `baseline_source_basis_drift.py`) that, given
  the active `weather_adjusted_model` baseline and current active facts, returns
  a structured, **value-based** verdict per baseline-driving field and an
  overall state:
  - `up_to_date` — recorded basis value matches the current promoted fact value.
  - `drifted` — a current active fact's value differs from the baseline's
    recorded basis value (the genuine drift case).
  - `basis_unknown` — the baseline has **no** recorded basis snapshot
    (non-bridge baseline); report informationally, never as drift.
  - `no_fact_lineage` — reviewer-supplied field with no fact source (cannot
    drift via facts).
  - `source_retired` — the basis fact is now retired/superseded with no active
    replacement.
- Comparison: recompute `_signature`-equivalent over **current** active facts ∪
  the baseline's recorded reviewer values and compare to the stored
  `source_fact_signature`; additionally produce per-field value diffs. The plain
  `_coerce_number` helper returns `None` for unit-bearing strings (e.g.
  `"340 Wp"`, `"66 kWac"`), so the comparator must normalize units explicitly —
  reuse the bridge's `input_norm.propose()` normalization + confirmation
  semantics (after `_unwrap`) or a dedicated unit parser — rather than relying on
  `_coerce_number` alone, which would wrongly treat text-with-unit facts as
  missing.
- Strictly read-only: no writes, no commits, no promotion, no baseline edit.

### Phase D2 — Surface in the existing read payloads (no migration)

- Extend the reconciliation readiness block and/or the baseline read with an
  additive, nullable `source_basis_drift` object: `{ state, drifted_fields[],
  unknown_basis: bool, detected_against_fact_ids[], note }`. Keep the existing
  `active_baseline_outdated` per-field warning but **re-derive it from the
  value-based resolver** so the false positives in G1/G3 disappear.
- Optionally a dedicated read-only endpoint
  `GET /api/telemetry/v2/sites/{site_id}/baselines/{id}/source-basis-drift`
  (Diligence/asset-view + company-visibility), zero writes.

### Phase D3 — Frontend display (no migration)

- Baseline-level drift badge in `ValidationHistoryPanel` / the active-baseline
  card and a one-line drift summary in `ReadinessSummary`, with the existing
  copy "Rebuild the active baseline to include the latest promoted value." Honor
  honest states: `basis_unknown` shows "source basis not recorded" (neutral),
  never a red "drift."

### Phase D4 — (Optional, deferred) Drift acknowledgement ledger

- If the business wants "reviewed & accepted as known drift," add an append-only
  acknowledgement table keyed on `(baseline_id, basis_signature)` mirroring the
  inventory-reconciliation acknowledgement model. **This** is the only phase
  that needs a migration; it remains informational and never changes baseline
  status. Recommended only after D1–D3 prove the read model.

---

## 6. Affected files / routes / models (for a future build — none changed here)

**Backend (read/derive):**

- `app/services/due_diligence/reconciliation_service.py` — re-derive
  `W_ACTIVE_OUTDATED` from the value-based resolver; add `source_basis_drift` to
  the readiness block.
- New `app/services/telemetry/baseline_source_basis_drift.py` — the resolver
  (would reuse `_unwrap`, `_coerce_number`, `_signature` semantics from
  `baseline_from_facts_service.py`).
- `app/schema/reconciliation.py` (+ `app/schema/telemetry_v2.py` if a dedicated
  endpoint is added) — additive nullable response fields.
- `app/routers/due_diligence/reconciliation.py` — unchanged contract; optional
  new read-only route under `app/routers/telemetry/v2.py`.

**Backend (read-only inputs, unchanged):** `app/models/telemetry_expected.py`,
`app/models/project_facts.py`, `app/crud/telemetry_expected.py`,
`app/services/promotion_service.py`, `app/services/telemetry/baseline_from_facts_service.py`.

**Routes touched (additive/derive only):**
`GET /api/due-diligence/sites/{site_id}/reconciliation`
(auth: `Diligence:view`, `get_authorized_site`); optional new
`GET /api/telemetry/v2/sites/{site_id}/baselines/{id}/source-basis-drift`.

**Frontend:**
`src/api/reconciliation.ts` (+ telemetry V2 client) for the new nullable fields;
`Reconciliation/components/ValidationHistoryPanel.tsx`, `ReadinessSummary.tsx`,
`DraftBaselineReviewPanel.tsx`, the `StatusCell`/table, and `utils.ts`.

---

## 7. Migration impact

- **Phases D1–D3: none.** All inputs already exist (`model_parameters_json`,
  header pointers, typed snapshot, live `project_facts`). The recommended core
  is purely read-only/on-read and additive in the response schema.
- **Phase D4 (optional, deferred):** one **additive** migration for an
  append-only drift-acknowledgement table (nullable FKs, no backfill, no
  destructive change), only if acknowledgement is desired.
- A future hardening option (not required): promote `source_fact_signature` to a
  typed nullable column for indexable drift queries — additive, nullable,
  back-compatible. Not recommended for the first phase.

---

## 8. Mutation boundaries

**Must NOT change (frozen):**

- Expected math / `expected_service`, the weather-adjusted formula, and any
  stored/active baseline values (active baseline stays immutable; replaced only
  via supersede).
- Baseline lifecycle (`approve` / `activate` / supersede), the single-active
  partial unique index, and `can_drive_expected` (frozen to
  `{inverter, module, weather_station}`).
- Authorization, WS.5, weather semantics, device mapping, ingestion contracts,
  O&M charts, the scheduler.
- **No** auto-deactivation, auto-recalculation, historical-expected rewrite, or
  silent fact promotion / source replacement.
- **Site 4 rows** (facts and baselines) — read-only.

**MAY change (additive, read-only):** new read-only drift resolver; additive
nullable fields on reconciliation/baseline read payloads; an optional new
read-only endpoint; frontend display. (Phase D4 only: an additive
acknowledgement table.)

---

## 9. Test plan (for a future build)

**Backend unit (resolver, pure, read-only):**

- Value-equal current fact vs. recorded basis → `up_to_date` (covers the Site 4
  false-positive: new fact id, same value ⇒ **not** drift).
- Value-changed current fact → `drifted` with the field listed.
- Re-promotion to same value, new `fact_id` → `up_to_date` (G1).
- Active baseline with empty `source_facts` / NULL `source_project_fact_id` →
  `basis_unknown`, **not** `drifted` (G3).
- Reviewer-supplied field (no fact) → `no_fact_lineage` (G2).
- Text-with-unit fact (`"340 Wp"`) vs. numeric snapshot `340.0` → equal **only
  after explicit unit-aware normalization**. Note `_coerce_number` alone returns
  `None` for unit-bearing strings, so the comparator must reuse the bridge's
  `input_norm.propose()` normalization/confirmation semantics (or a dedicated
  unit parser); a naive numeric coercion would wrongly treat `"340 Wp"` as
  missing.
- Basis fact retired with no active replacement → `source_retired`.
- No active baseline / no facts → empty, honest result (no 500).
- Assert the resolver performs **zero** writes/commits (count flushes).

**Backend integration:** reconciliation endpoint returns the additive
`source_basis_drift` block and the re-derived `active_baseline_outdated` without
mutating anything; superseded/draft baselines are ignored.

**Harness notes:** ilios-server pytest needs `test_db_name` + a separate DB; run
client-based tests with `telemetry_scheduler_enabled=false` (lowercase,
case-sensitive) so the lifespan scheduler does not hang; no `pytest-mock` (use
`monkeypatch`); `PermissionType` is a plain `str`.

**Frontend:** component tests for the baseline-level badge (drift / up-to-date /
`basis_unknown` neutral), the readiness summary line, and that `basis_unknown`
never renders a red drift state.

---

## 10. Browser-validation plan (for a future build)

All steps are **read-only observation** (no Site 4 mutations):

1. Project Hub → Site 4 (110 Shawmut) → **Reconciliation** tab. Today: confirm
   the four fact-backed fields show `active_baseline_outdated` /
   `blocks_reporting` even though values match (the false positive). After D1–D3:
   confirm they show `up_to_date` and the baseline-level summary shows
   `basis_unknown` for active baseline #4 (no recorded snapshot) — not "drift."
2. Positive drift case (a non-protected site): build a draft from facts →
   approve → activate; then re-promote a physics fact to a **different** value;
   confirm the field shows `drifted` and the action reads "Rebuild the active
   baseline…", while the **expected line, baseline status, and active row are
   unchanged**.
3. Equal-value re-promotion (a non-protected site): re-promote the same value;
   confirm **no** drift is shown (G1 fixed).
4. Confirm the expected/O&M chart and baseline status never change as a result
   of any drift state, and that no write occurs (network calls are GET-only for
   the reconciliation/drift surfaces).

---

## 11. Site 4 read-only assessment (#3 / #4 source-basis history)

Captured via read-only `SELECT`s only. **No Site 4 rows were modified.**

**Active promoted facts (status `active`):**

| fact_id | field | value | promoted_at |
| --- | --- | --- | --- |
| 114 | module_wattage | `{"v": "340 Wp"}` | 2026-06-18 |
| 115 | module_quantity | `{"v": "1900"}` | 2026-06-18 |
| 118 | inverter_wattage | `{"v": "66 kWac"}` | 2026-06-18 |
| 119 | inverter_quantity | `{"v": "7"}` | 2026-06-18 |

**Baseline #3 (superseded, v1):** `source_project_fact_id = 114`,
`source_document_id = 912`, `active_from = 2026-05-11`,
`active_to = 2026-06-20 16:33:48` (closed when #4 activated). Full bridge basis
snapshot present — `source_facts` = module_wattage 340 (fact 114), module_quantity
1900 (115), inverter_wattage 66 (118), inverter_quantity 7 (119), plus a
`source_fact_signature`. This is a textbook bridge-built baseline.

**Baseline #4 (active, v2):** `supersedes_baseline_id = 3`,
`validation_policy_version = baseline-physics-v1`,
`created_at = approved_at = active_from = 2026-06-20 16:33`. Typed columns:
`module_wattage = 340`, `module_quantity = 1900`, `inverter_wattage = 66`,
`inverter_quantity = 7`, `thermal_coefficient_pct = -0.35`,
`cec_efficiency_pct = 97`, `pto_date = 2026-05-11`.
**`source_project_fact_id = NULL`, `source_document_id = NULL`,
`source_fact_signature = NULL`, `source_facts = none`.** Its
`model_parameters_json` contains only a human-authored `replacement` block
documenting the correction of #3's invalid `thermal_coefficient_pct` (350.0 →
-0.35) and `power_tolerance_min_pct` (5.0 → 0.0), and which fields were carried
over from #3.

**Assessment:**

- #4 was created by a **manual replacement/correction path**, not the bridge, so
  it carries **no source-basis snapshot**.
- Under today's logic, `_baseline_source_fact_ids(#4)` = ∅, so for every
  fact-backed `HEADER_COLUMN` field with an active fact,
  `active_fact.id not in ∅` is true ⇒ `W_ACTIVE_OUTDATED` fires for **all four**
  fields — despite the values matching the current facts exactly (340 / 1900 /
  66 / 7). This is a **false positive** and the clearest justification for G1
  (value-based comparison) and G3 (`basis_unknown` ≠ drift).
- The fact values are **text-with-unit** (`"340 Wp"`, `"66 kWac"`) while the
  baseline columns are numeric — any value-based comparator must normalize units
  explicitly. `_coerce_number` alone returns `None` for `"340 Wp"`/`"66 kWac"`,
  so it must reuse the bridge's `input_norm.propose()` normalization/confirmation
  semantics (or a dedicated unit parser); a naive numeric coercion would wrongly
  treat these as missing and mis-flag.
- Governance is currently honored on Site 4: #4 remains active, expected output
  is unchanged, and #3 was superseded (not edited) — the drift surfaces only as
  read-only reconciliation warnings.

---

## 12. Confirmation: no production code changed

- **No production code was modified.** The only file created by this sprint is
  this document: `docs/baseline_source_basis_drift_staleness_audit.md`.
- **No migrations** were created or run.
- **No expected-model, lifecycle, authorization, WS.5, weather-semantics, or
  device-mapping changes** were made.
- **No Site 4 mutations.** All Site 4 inspection used read-only `SELECT`
  statements; facts and baselines #3/#4 are unchanged.
- All recommendations in §5–§10 are **proposals for a future build**, not
  applied changes.
