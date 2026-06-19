# Expected Baseline Readiness Input Resolution Audit

**Type:** Audit & design sprint (no implementation)
**Status:** Complete — design recommendations only; no code, migrations, endpoints, UI, or data-model changes were made.
**Scope of subject system:** DD V2 → expected-baseline bridge, weather-adjusted expected physics, design-estimate points, reconciliation, and the Baseline Readiness panel.
**Date:** 2026-06-19

---

## 0. How to read this document

This audit answers one strategic question:

> For every input the expected-baseline pipeline needs, **where should the value come from, does it already exist anywhere in the diligence/document/`project_facts` chain, why is it not usable today, and what is the right UX to resolve it** — without guessing values, fabricating physics, or silently normalizing.

It is organized exactly to the requested areas **A–L**. Section 1 is an executive summary; Section 2 fixes the vocabulary (the 9-stage lineage) so the rest of the document is unambiguous. Every claim is grounded in a code citation of the form `path:line`.

### Constraints honored by this audit

This is a **read-only** audit. It created **no** baselines, promoted **no** facts, normalized **no** values, changed **no** expected math, telemetry ingestion, WeatherResolver, device eligibility, O&M analytics, reconciliation, or extraction. It uses **no** SAFL value as a V2 baseline source and reintroduces **no** BigQuery/Firestore/legacy path. It only reads code and recommends.

---

## 1. Executive summary

### 1.1 The three observed blockers are really *two* root causes plus a UX gap

The Baseline Readiness panel reports "draft weather-adjusted baseline not ready, no active baseline, design-estimate points 0/12." Tracing every input to source shows this collapses to **two underlying mechanical causes and one structural UX gap**:

1. **Root cause A — Non-numeric active facts (`module_wattage="340 Wp"`, `inverter_wattage="66 kWac"`).**
   These two values *do exist* as promoted active `project_facts`, but they are stored verbatim as text-with-unit (`{"v": "340 Wp"}`). The readiness evaluator coerces fact values with `float()` after only stripping commas/whitespace (`baseline_from_facts_service.py:162-179`). `float("340 Wp")` raises `ValueError`, so the field is **treated as missing** with a warning (`baseline_from_facts_service.py:264-270`). This is *why the same two fields appear in BOTH the "missing required physics fields" list AND the "non-numeric promoted active facts" list* — they are the same defect surfaced twice.

2. **Root cause B — Five required physics constants have no fact source at all.**
   The weather-adjusted physics requires **nine** fields (`expected_service.py:81-91`). Only **four** (module/inverter wattage + quantity) are captured as `project_facts` (`baseline_from_facts_service.py:51-56`). The other five — `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct` — have **no seeded extraction/catalog/bridge fact source today** (no extraction-registry coverage, no baseline-driving canonical mapping in `FACT_FIELD_TO_COLUMN`, no reconciliation-catalog row). The canonical store *could* in principle hold a manually-created field of that name, but none feeds the bridge. They are therefore *reviewer-supplied only*, on the create-draft request payload (`baseline_from_facts_service.py:70-72, 312-318`).

3. **The structural UX gap — readiness is computed facts-only, with no place to supply the reviewer constants.**
   `evaluate_readiness` calls the evaluator with `reviewer_values=None` (`baseline_from_facts_service.py:464-476`). Therefore the five reviewer-only constants are **always reported as missing** in the readiness panel, and there is **no in-panel action** to supply them, normalize the two text-with-unit facts, or even see *why* a field is unusable beyond a flat "missing." The panel is honest but **non-actionable** for exactly the fields that are blocking.

### 1.2 The optional inputs are silently defaulted, not surfaced honestly

`dc_loss_pct`, `ac_loss_pct`, `medium_voltage_loss_pct`, `mv_line_loss_pct` default to **0%** and `soiling_factor` defaults to **1.0** (`expected_service.py:137-141`). The evaluator emits a free-text warning when they are absent (`baseline_from_facts_service.py:338-355`), but there is **no structured, field-level "default applied" indicator** in readiness or reconciliation. A 0% loss / no-soiling assumption is materially optimistic and must be labeled as an applied default, not presented as fact.

### 1.3 PTO absence suppresses the *entire* expected curve, not just "before PTO"

When `pto_date is None`, **every** bucket is returned `pre_pto` with `expected_power_kw=None` (`expected_service.py:315-328`). So "expected is NULL before PTO" is, in the missing-PTO case, "expected is NULL **everywhere**." PTO absence is *not* a draft-creation blocker (it is only a warning, `baseline_from_facts_service.py:357-365`), but it fully suppresses the expected chart until a PTO date is supplied on the baseline.

### 1.4 Design-estimate points 0/12 is a separate, non-blocking pipeline

Design-estimate points come from a *different* producer (`baseline_points_service.py`) driven by monthly/annual production facts, **not** from the physics readiness path. 0/12 means no monthly *points* are currently represented/evaluable — most commonly because no monthly production facts are promoted, but it can also occur when no design-estimate baseline exists yet, or when monthly facts are present but non-numeric. The generator deliberately **never distributes an annual total into months** and assumes a kWh unit it does not verify. This is its own flow (upload PVsyst → extract → accept/promote → create design-estimate baseline → generate points) and is independent of the weather-adjusted draft readiness.

### 1.5 The headline recommendation

The safest practical first implementation is **(1) a normalization guard + confirm-on-acceptance for text-with-unit numeric fields** (fixes Root cause A auditably), **(2) a "reviewer-supplied baseline input" capture surface** in Baseline Readiness for the five datasheet constants (fixes Root cause B), and **(3) richer readiness/reconciliation indicators** (`value_present_but_not_numeric`, `reviewer_supplied_input_needed`, `default_applied_optional_input`, `pre_pto_expected_suppressed`) so the panel becomes actionable. No value is ever auto-normalized without an explicit, auditable, user-confirmed rule. Full phasing in **Section K**.

---

## 2. Vocabulary — the lineage that must never be collapsed

The platform invariant is: *never let accepted/promoted/baseline/O&M state silently survive an upstream source change.* That requires keeping these nine stages distinct. This audit uses these terms precisely throughout.

| # | Stage | Where it lives | Mutability |
|---|-------|----------------|------------|
| 1 | **Raw extracted value** | `AIParsingResult.parsed_result` (JSON; string-valued, e.g. `"340 Wp"`) | Immutable per parse run |
| 2 | **Accepted value** | `document_keys.value` / `override_value` (String) | Reviewer action |
| 3 | **Promoted `project_fact`** | `project_facts.value` JSONB envelope `{"v": ...}` (`models/project_facts.py:43`); status `candidate`→`active`→`retired` | Promotion lifecycle |
| 4 | **Normalized baseline input** | *Does not exist as a persisted stage today* — coercion happens transiently in `_coerce_number` | — |
| 5 | **Draft baseline** | `telemetry_expected_baselines` rows, `status='draft'` | Bridge create |
| 6 | **Active baseline** | `telemetry_expected_baselines` rows, `status='active'` (single-active partial unique index) | Approve+activate |
| 7 | **Design-estimate points** | `telemetry_expected_baseline_points` rows (`baseline_type='design_estimate'`) | Points generator |
| 8 | **Weather-adjusted expected** | Computed on read by `expected_service.compute_expected_buckets` | Derived |
| 9 | **Actual telemetry** | V2 rollups (`telemetry_*_rollups`) | Ingestion |

**Key structural observation:** stage **4 (normalized baseline input) is missing as an explicit, auditable artifact.** Today a fact's value is coerced to a number *at the moment a draft is built*, transiently, with no persisted record of "this raw `340 Wp` was interpreted as `340 W`." This is the single most important gap behind both Root cause A and the normalization-UX question (Sections C and G).

---

## A. Required baseline input inventory

Every input consumed by `create-draft-from-facts` / `baseline_from_facts_service`, the expected physics model (`expected_service`), the design-estimate points generator (`baseline_points_service`), and the O&M expected/comparative displays.

### A.1 Required physics fields (block the weather-adjusted draft)

Source of the required set: `REQUIRED_PHYSICS_FIELDS` (`expected_service.py:81-91`). The fact-backed subset: `FACT_FIELD_TO_COLUMN` (`baseline_from_facts_service.py:51-56`). The reviewer-only subset is the set difference (`baseline_from_facts_service.py:70-72`).

| Canonical key | Display label | Req? | Type | Unit | Must be numeric? | Text-with-unit today? | Reviewer-suppliable? | Source-backed (document)? | Default? | Default safe/approved? | If missing |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `module_wattage` | Module Wattage | Required | float | **W** (watts) | Yes | **Rejected** (→ treated missing) | No (fact-only path) | Yes (PVsyst/datasheet) | None | — | **Blocks draft** |
| `module_quantity` | Module Quantity | Required | float | count | Yes | Rejected | No (fact-only) | Yes (PVsyst) | None | — | **Blocks draft** |
| `inverter_wattage` | Inverter Wattage | Required | float | **kW (AC)** | Yes | **Rejected** | No (fact-only) | Yes (PVsyst/datasheet) | None | — | **Blocks draft** |
| `inverter_quantity` | Inverter Quantity | Required | float | count | Yes | Rejected | No (fact-only) | Yes (PVsyst) | None | — | **Blocks draft** |
| `thermal_coefficient_pct` | Thermal Coefficient (%/°C) | Required | float | % per °C | Yes | n/a (no fact path) | **Yes (only path)** | Should be (module datasheet) — **not extracted today** | None | — | **Blocks draft** |
| `power_tolerance_min_pct` | Power Tolerance (min %) | Required | float | % | Yes | n/a | **Yes (only path)** | Should be (module datasheet) — not extracted | None | — | **Blocks draft** |
| `year_1_degradation_pct` | Year-1 Degradation (%) | Required | float | % | Yes | n/a | **Yes (only path)** | Should be (warranty/PVsyst) — not extracted | None | — | **Blocks draft** |
| `annual_degradation_pct` | Annual Degradation (%) | Required | float | % | Yes | n/a | **Yes (only path)** | Should be (warranty/PVsyst) — not extracted | None | — | **Blocks draft** |
| `cec_efficiency_pct` | CEC Efficiency (%) | Required | float | % | Yes | n/a | **Yes (only path)** | Should be (inverter datasheet/CEC listing) — not extracted | None | — | **Blocks draft** |

> **Unit hazard (critical):** `module_wattage` is in **watts** but `inverter_wattage` is in **kilowatts** — the physics computes `dc_nameplate_kw = module_wattage * module_quantity / 1000` and `ac_nameplate_kw = inverter_wattage * inverter_quantity` (`expected_service.py:271-272`). The two "wattage" fields therefore use **different base units**. The only guardrail today is a plausibility *warning* (`module_wattage < 50` looks like kW; `inverter_wattage > 1000` looks like W) that **never auto-converts** (`baseline_from_facts_service.py:216-229`).

### A.2 Optional supplemental inputs (default applied; warning only)

`BaselineParams` defaults (`expected_service.py:137-141`); evaluator handling (`baseline_from_facts_service.py:325-355`).

| Canonical key | Display label | Req? | Type | Unit | Default | Default safe/approved? | If missing |
|---|---|---|---|---|---|---|---|
| `dc_loss_pct` | DC Loss (%) | Optional | float | % | **0.0** | Optimistic — *not* independently approved | Default + free-text warning |
| `ac_loss_pct` | AC Loss (%) | Optional | float | % | **0.0** | Optimistic | Default + warning |
| `medium_voltage_loss_pct` | MV Loss (%) | Optional | float | % | **0.0** | Optimistic | Default + warning |
| `mv_line_loss_pct` | MV Line Loss (%) | Optional | float | % | **0.0** | Optimistic | Default + warning |
| `soiling_factor` | Soiling Factor | Optional | float | ratio (1.0 = none) | **1.0** | Optimistic (no soiling) | Default + warning |
| `pto_date` | PTO Date | Optional for draft | date | — | None | n/a | Warning; **suppresses entire expected curve** (Section I) |

> Reviewer-supplied loss values are sign-normalized to a positive percent (`abs()`) because the formula subtracts a positive % (`baseline_from_facts_service.py:332`, mirrored in `expected_service.py:41-42`).

### A.3 Design-estimate point inputs (separate producer)

Producer `baseline_points_service.py`; catalog `reconciliation_catalog.py:92-104, 157-170`.

| Canonical key(s) | Display label | Req? | Type | Unit | Default | If missing |
|---|---|---|---|---|---|---|
| `january_…december_estimated_production_year_1` (12) | Monthly Estimated Production (Yr 1) | Optional | float | kWh (**assumed, unit_verified=false**) | None | Month point skipped → contributes to **0/12** |
| `estimated_production_year_1` | Annual Estimated Production (Yr 1) | Optional | float | kWh (assumed) | None | Annual point skipped |
| `p50_mwh`, `p90_mwh`, `statistical_standard_p50_or_p90` | P50/P90 scenarios | Optional | float/text | MWh | None | Metadata-only (header block) |
| `…estimated_ghi_irradiance_per_meter_squared` (monthly + annual) | Estimated GHI | Optional | float | kWh/m² | None | Metadata-only |

> The generator **never distributes an annual total into months** and **never fabricates** points; it stores production values as-extracted into `expected_energy_kwh` with `unit_verified=false` (`baseline_points_service.py:14-15, 459`).

### A.4 What "missing" does, by class

- **Required physics (9):** any missing → `ready=False`, draft creation returns not-ready (HTTP 422 `review_required`), and even if a baseline row somehow existed, `BaselineParams.from_baseline` raises `ValueError` for a missing required field (`expected_service.py:145-161`). So expected cannot compute.
- **Optional (losses/soiling):** never blocks; default applied silently with a warning.
- **PTO:** never blocks draft; suppresses expected (Section I).
- **Design-estimate points:** never blocks the weather-adjusted draft; only affects the design-estimate comparison curve.

---

## B. Source tracing

For each required baseline input, where the value can live and whether it is usable for baseline creation **today**.

### B.1 The four fact-backed physics fields (`module_wattage`, `module_quantity`, `inverter_wattage`, `inverter_quantity`)

These can flow through the full chain:

- **Uploaded document → parsed AI result → `document_key` → accepted/overridden → candidate `project_fact` → active `project_fact`.** Confirmed path; `ProjectFact.value` stores the envelope `{"v": <string>}` verbatim (`models/project_facts.py:43`).
- **Draft / active baseline `model_parameters_json`:** the bridge records `field_sources` and `source_facts` with `fact_id`, `document_id`, and `ai_confidence` for full provenance (`baseline_from_facts_service.py:288-305, 535-543`).
- **Authoritative?** Yes — the active `project_fact` is the authoritative source. SAFL is **display-only** (`reconciliation_catalog.py:188-203`) and is never read by the bridge (`baseline_from_facts_service.py:13-16, 563`).
- **Usable today?** **Only if the active fact value is bare-numeric.** With `"340 Wp"`/`"66 kWac"` it is *not usable* (Root cause A). The provenance (`document_id`, `fact_id`, `ai_confidence`, accepted/promoted status) is all available to surface in UX.

### B.2 The five reviewer-only physics constants

- **Exists in any document/fact stage?** **No seeded source today.** No extraction coverage (Section D), no `document_key`, no `project_fact`, and no baseline-driving canonical mapping — confirmed absent from `FACT_FIELD_TO_COLUMN` and from `RECONCILIATION_CATALOG`. (A manually-created canonical field of the same name is theoretically possible but does not feed the bridge.)
- **Only home today:** transient — the `reviewer_values` payload to `create-draft-from-facts`, persisted only into the resulting draft's `model_parameters_json.field_sources[...] = {"source": "reviewer_supplied"}` and the baseline header columns (`baseline_from_facts_service.py:312-323, 540`).
- **Usable today?** Only by a reviewer typing them at create time — and the readiness panel never offers that input (Section 1.3).

### B.3 Optional losses / soiling

- **Exists?** No fact source. A **display-only** legacy comparison exists via `SAFL_FIELD_MAP` (`dc_loss_pct→dc_wiring_loss`, etc., `reconciliation_catalog.py:192-203`) compared on magnitude (`ABS_COMPARE_FIELDS`, `:206-208`). **Legacy values are never used to build a V2 baseline.**
- **Usable today?** Reviewer-supplied on create only; otherwise defaulted.

### B.4 PTO

- **Exists?** PTO is extractable from EPC agreements (Section D) and appears in legacy SAFL as `permission_to_operate` (`reconciliation_catalog.py:197-198`), but it is **not** wired as a baseline-driving `project_fact` into the bridge. On the baseline it is the `pto_date` column, reviewer-supplied at create (`baseline_from_facts_service.py:357-360`; column at `models/telemetry_expected.py:193`).
- **Usable today?** Reviewer-supplied on create only.

### B.5 Design-estimate production (monthly/annual)

- **Exists?** Monthly + annual production **are** extractable from PVsyst (Section D) and are catalog fields with `baseline_target = POINTS_MONTHLY/POINTS_ANNUAL` (`reconciliation_catalog.py:92-104, 157-163`). They flow as normal `project_facts`.
- **Usable today?** Yes, *if* accepted/promoted — but they feed the **design-estimate** producer, a separate action from the weather-adjusted draft (Section H).

### B.6 Source-tracing summary table

| Input | Document-extractable? | Reaches `project_fact` today? | Reconciliation row today? | Reviewer-suppliable? | Usable for baseline today |
|---|---|---|---|---|---|
| module_wattage | Yes (PVsyst) | Yes | **Yes** | (fact path) | Only if numeric |
| module_quantity | Yes | Yes | **Yes** | (fact path) | Yes |
| inverter_wattage | Yes | Yes | **Yes** | (fact path) | Only if numeric |
| inverter_quantity | Yes | Yes | **Yes** | (fact path) | Yes |
| thermal_coefficient_pct | **No** | No | **No** | Yes | Reviewer-only |
| power_tolerance_min_pct | **No** | No | **No** | Yes | Reviewer-only |
| year_1_degradation_pct | **No** | No | **No** | Yes | Reviewer-only |
| annual_degradation_pct | **No** | No | **No** | Yes | Reviewer-only |
| cec_efficiency_pct | **No** | No | **No** | Yes | Reviewer-only |
| dc/ac/mv loss (×4) | No | No | **No** (SAFL display-only) | Yes | Defaulted 0% |
| soiling_factor | No | No | **No** | Yes | Defaulted 1.0 |
| pto_date | Yes (EPC) | No (not wired) | **No** (SAFL display-only) | Yes | Reviewer-only |
| monthly/annual production | Yes (PVsyst) | Yes | **Yes** (design-estimate) | (fact path) | Yes (design-estimate flow) |

---

## C. Non-numeric value analysis — `"340 Wp"` and `"66 kWac"`

### C.1 Where the values came from

The AI parser stores the raw extracted string verbatim — it does **not** separate numeric value and unit (`AIParsingResult.parsed_result`, e.g. `{"module_wattage": {"value": "340 Wp", ...}}`). That string survives unchanged through `document_key.value` (String) → accepted/override value → candidate fact → active fact `{"v": "340 Wp"}`. **No stage parses out the unit.** There is no separate unit-metadata column anywhere in the chain.

### C.2 What the canonical field / engine expects

- The baseline engine expects **bare numeric** floats: `module_wattage` in **W**, `inverter_wattage` in **kW (AC)** (`expected_service.py:271-272`).
- The coercion helper does only `raw.strip().replace(",", "")` then `float(...)` (`baseline_from_facts_service.py:171-178`). `float("340 Wp")` and `float("66 kWac")` both raise `ValueError` → coerced to `None` → field counted as **missing** (`:264-270`).

### C.3 Is there a normalization helper?

**No.** There is no unit-stripping or unit-conversion helper anywhere in the backend. The only related logic is `_unit_warnings`, which *flags* implausible magnitudes but explicitly **never converts** (`baseline_from_facts_service.py:216-229`). The reconciliation service has its own `_coerce_number` with the same float-only behavior (read-only; no normalization).

### C.4 Per-value verdict

| Value | Field expects | Numeric content | Unit qualifier | Verdict |
|---|---|---|---|---|
| `"340 Wp"` | W | 340 | `Wp` = watt-peak = **watts** (matches) | **Safe normalization with explicit unit** → `340`. No conversion needed; only strip the unit token. |
| `"66 kWac"` | kW (AC) | 66 | `kWac` = kilowatts AC (matches field's AC-nameplate meaning) | **Safe normalization with explicit unit** → `66`. No conversion needed. |

**Counter-examples that are NOT safe** (must require confirmation, never auto-applied):

- `"66000 Wac"` for `inverter_wattage` → would need ÷1000 → **unsafe normalization requiring unit conversion** (W→kW).
- `"340"` with no unit for a field where W vs kW is ambiguous → **missing unit**; confirm before trusting.
- `"0.34 kW"` for `module_wattage` → **ambiguous/likely wrong canonical mapping** (module in kW is implausibly small; `_unit_warnings` would flag `<50`).
- A value that is actually inverter *DC* rating mapped onto an AC field → **wrong canonical mapping**, not a unit problem.

### C.5 Where to solve it

The transformation must be **explicit, auditable, and reversible to its raw source** (lineage stage 4 must become real). Therefore:

- **Do NOT solve silently in `_coerce_number`** (that is invisible auto-normalization — violates the constraint).
- **Best layer: acceptance/promotion**, where a human is already in the loop and the system already records provenance — capture `display_value` (`"340 Wp"`) *and* `numeric_value`/`unit` together, so the active fact carries an auditable normalized value. **Second-best: a baseline-readiness "confirm unit" step** that records a reviewer-confirmed normalized baseline input without mutating the historical raw fact.
- **Parser-only separation** (emit `numeric_value`+`unit`) is the cleanest long-term but the highest-effort and does not retroactively fix existing facts.

Full options comparison and recommendation in **Section G**.

---

## D. Missing input source recommendations

Expected source-of-truth, current coverage, and recommended UX for each missing field. Coverage verified against `configs/ai_parsing_config.json`, the canonical-field seed (`dev_scripts/seed_canonical_fields.py`), and the extraction registry (`models/extraction_registry.py`, `dev_scripts/seed_extraction_registry.py`).

| Field | Expected source-of-truth doc | Parser coverage today | Extraction-registry field today | Generic parser can extract? | Specialized schema exists? | Data Room should request upload? | Reviewer-supplied acceptable? | Readiness "supply value" action? |
|---|---|---|---|---|---|---|---|---|
| `module_wattage` | Module datasheet / PVsyst / equipment schedule | **Yes** (PVsyst) | Yes | Yes | Yes (PVsyst) | If absent | Via fact override | Normalize/confirm |
| `inverter_wattage` | Inverter datasheet / PVsyst / equipment schedule | **Yes** (PVsyst) | Yes | Yes | Yes (PVsyst) | If absent | Via fact override | Normalize/confirm |
| `thermal_coefficient_pct` | **Module datasheet** | **No** | **No** | Maybe (low confidence) | **No** | **Yes** (module datasheet) | **Yes** | **Yes (add)** |
| `power_tolerance_min_pct` | **Module datasheet** | **No** | **No** | Maybe | **No** | **Yes** | **Yes** | **Yes (add)** |
| `year_1_degradation_pct` | **Warranty / PVsyst / diligence assumption** | **No** | **No** | Maybe | **No** (O&M has generic "Degradation") | **Yes** (warranty/PVsyst) | **Yes** | **Yes (add)** |
| `annual_degradation_pct` | **Warranty / PVsyst / diligence assumption** | **No** | **No** | Maybe | **No** | **Yes** | **Yes** | **Yes (add)** |
| `cec_efficiency_pct` | **Inverter datasheet / CEC listing** | **No** | **No** | Maybe | **No** | **Yes** (inverter datasheet) | **Yes** | **Yes (add)** |
| `dc/ac/mv loss (×4)` | PVsyst loss diagram / engineering | **No** | **No** | Maybe | **No** | Optional | **Yes** | Optional (default labeled) |
| `soiling_factor` | PVsyst / O&M assumption | **No** | **No** | Maybe | **No** | Optional | **Yes** | Optional (default labeled) |
| `pto_date` | **Utility/interconnection / PTO letter / commercial-operations** | **Yes** (EPC agreement) | Yes | Yes | Yes (EPC) | If absent | **Yes** | **Yes (add)** |
| `system_size_dc` | PVsyst / PPA / EPC / interconnection | **Yes** | Yes | Yes | Yes | — | Yes | — |
| `system_size_ac` | PVsyst | **Yes** | Yes | Yes | Yes | — | Yes | — |
| `module_quantity` | PVsyst / equipment schedule | **Yes** | Yes | Yes | Yes | — | (fact path) | — |
| `inverter_quantity` | PVsyst / equipment schedule | **Yes** | Yes | Yes | Yes | — | (fact path) | — |
| `annual production` | **PVsyst / design estimate** | **Yes** | Yes | Yes | Yes | If absent | (fact path) | Design-estimate flow |
| `monthly production` | **PVsyst / design estimate** | **Yes** | Yes | Yes | Yes | If absent | (fact path) | Design-estimate flow |

### D.1 Recommendation pattern

There are two distinct gap classes:

1. **Extractable but not yet captured (PTO, and reinforcing module/inverter).** PTO is already extractable from EPC documents — but note a naming/normalization gap: the EPC config field is `PTO` (normalizes to canonical `pto`), whereas the bridge expects a reviewer-supplied `pto_date`. So even an extracted PTO does not flow to the baseline today; the gap is that PTO is **not wired** (and not unit/format-aligned) as a baseline input. Recommendation: align the canonical PTO field, add PTO to the reconciliation catalog and to the readiness/create flow as a source-backed value (with reviewer override), and offer "Upload PTO letter / interconnection approval" when absent.
2. **Datasheet constants with no extraction (the five physics constants + losses + soiling).** These are stable per-equipment-model engineering constants, not per-site commercial terms. Recommendation, in priority order:
   - **(a)** Allow **reviewer-supplied** entry in Baseline Readiness with provenance (`reviewer_supplied`, who/when/why) — *lowest risk, immediate*.
   - **(b)** Add a **specialized "Module Datasheet" and "Inverter Datasheet" document type** to the extraction registry so these can become source-backed facts over time.
   - **(c)** Offer a **"Upload module/inverter datasheet"** action in the Data Room when a constant is needed but absent.

Reviewer-supplied is acceptable for all of these **provided provenance is recorded and the value is clearly labeled as reviewer-entered, not document-extracted.**

---

## E. Reconciliation status review

### E.1 Current status ladder (read-only)

`reconciliation_service.py` assigns the most-advanced-stage-wins status from this ladder (`:89-97`):
`missing` → `ai_extracted_only` → `accepted_document_value` → `candidate_only` → `accepted_not_promoted` → `active_fact` → `in_draft_baseline` → `in_active_baseline`; plus `superseded`.

Blocking levels (`_blocking_level`, `:634-655`): `blocks_baseline`, `blocks_expected`, `blocks_reporting`, `lowers_confidence`, `informational`. Required action via `_required_action` (`:604-631`); labels/explanations via `_STATUS_LABELS`/`_STATUS_EXPLANATIONS` (`:107-147`).

### E.2 Per-field coverage assessment

| Field | Reconciliation row today? | Current status for the user's site | Does the row correctly explain the blocker? |
|---|---|---|---|
| `module_wattage` (`"340 Wp"`) | **Yes** (`reconciliation_catalog.py:125-129`, `required_for_baseline=True`) | Reports `active_fact` (a value exists) — **does NOT detect non-numeric** | **No.** The row says "active fact / not yet on a baseline" but the real blocker is that the value is unusable. `_coerce_number` returns `None` silently (`:192-206`); there is no `value_present_but_not_numeric` state. **Misleading.** |
| `inverter_wattage` (`"66 kWac"`) | **Yes** | Same as above | **No** — same gap. |
| `module_quantity`, `inverter_quantity` | **Yes** | Correct (`active_fact`/`in_*_baseline`) | Yes |
| `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1/annual_degradation_pct`, `cec_efficiency_pct` | **No row at all** | n/a | **No.** These five hard blockers are **completely invisible** in reconciliation. The user has no row telling them these are required and reviewer-supplied. **Biggest reconciliation gap.** |
| `dc/ac/mv loss`, `soiling_factor` | **No row** (SAFL display-only map only) | n/a | No "default applied" indicator anywhere. |
| `pto_date` | **No catalog row** (SAFL display-only) | n/a | No row explaining pre-PTO suppression. |
| monthly/annual production | **Yes** (`POINTS_*`) | `missing`/`active_fact` with `blocks_expected` when absent | Partially — explains design-points gap but not that it is a separate generate step. |

### E.3 Recommended new statuses / indicators (recommend only — do NOT implement here)

- **`value_present_but_not_numeric`** — an active fact exists but `_coerce_number` returns `None` (e.g. `"340 Wp"`). *Blocking:* `blocks_baseline`. *Action:* "Normalize / confirm unit." **Highest-value addition.**
- **`unit_normalization_required`** — value parses to a number but carries a unit token requiring confirmation/conversion (e.g. `"66000 Wac"`). *Action:* "Confirm unit."
- **`reviewer_supplied_input_needed`** — a required field that has no fact source and no document path (the five constants). *Blocking:* `blocks_baseline`. *Action:* "Add reviewer-supplied baseline input." **Second-highest value** — surfaces the five invisible blockers.
- **`source_document_missing`** — required and extractable but no document uploaded (e.g. PTO when no EPC present). *Action:* "Upload source document."
- **`active_fact_exists_but_not_baseline_usable`** — superset framing for non-numeric/unit/ambiguous cases.
- **`source_value_ambiguous`** — multiple distinct accepted candidates or a unit that cannot be disambiguated. *Blocking:* `lowers_confidence`. (Overlaps existing `needs_review`.)
- **`baseline_required_missing`** — already effectively expressed via `required_for_baseline` + `missing` + `blocks_baseline`; keep, but extend the catalog to the five constants so it actually fires for them.
- **`default_applied_optional_input`** — optional loss/soiling absent and a default (0% / 1.0) will be applied. *Blocking:* `informational`. *Action:* "Optional — confirm or override default."
- **`pre_pto_expected_suppressed`** — PTO unknown/future so expected is suppressed. *Blocking:* `blocks_expected` (informational re baseline). *Action:* "Supply PTO date."

### E.4 Catalog change implied (design only)

To make reconciliation honest about the blockers, `RECONCILIATION_CATALOG` would need additive rows for the five reviewer-required constants (category `BASELINE_PHYSICS`, `baseline_target = HEADER_COLUMN`, `required_for_baseline=True`) plus PTO/losses/soiling as informational rows. **No write/normalization** — these are display + status-derivation rows only. (Implementation deferred to Section K, Phase 4.)

---

## F. Baseline Readiness UX design

Goal: turn the honest-but-flat panel into an **actionable** one. For each blocker, the panel should render the following fields.

### F.1 Per-row schema (design)

| Element | Source today | Example for `module_wattage="340 Wp"` |
|---|---|---|
| Field label | catalog `display_label` | "Module Wattage" |
| Required/optional | catalog `required_for_baseline` | Required |
| Current value (if any) | active fact raw value | `340 Wp` |
| Why not usable | **new** derivation | "Value is not a bare number — `Wp` unit present." |
| Source status | **new** enum (below) | `active fact but non-numeric` |
| Exact next action | **new** | "Normalize / confirm unit (340 W)" |
| Permission needed | existing perms model | `diligence:edit` / `assets_management:edit` |
| Blocking level | `_blocking_level` extended | `blocks draft baseline` |

### F.2 Source-status vocabulary (the panel's per-field state)

`missing` · `AI-extracted` · `accepted-not-promoted` · `active fact` · **`active fact but non-numeric`** · **`stale source`** (from the existing promotion freshness guard) · **`optional default applied`** · **`pre-PTO`**.

### F.3 Next-action vocabulary (each maps to one concrete control)

`Open Data Room` · `Accept value` · `Promote value` · **`Normalize / confirm unit`** · `Upload source document` · **`Add reviewer-supplied baseline input`** · `Create draft baseline` · `Activate baseline`.

### F.4 Blocking-level vocabulary

`blocks draft baseline` · `blocks active baseline` · `blocks expected` · `lowers confidence` · `informational`.

### F.5 The three concrete UX flows the panel must support

1. **Normalize a text-with-unit fact** (`340 Wp`, `66 kWac`): inline "Confirm unit" affordance showing raw value, proposed numeric, and detected unit; on confirm, records an auditable normalized baseline input (never silently mutating the raw fact). Gated to safe cases; conversion cases require explicit confirmation.
2. **Supply the five reviewer constants**: a "Baseline inputs (reviewer-supplied)" sub-panel with labeled numeric fields (units shown), each stamped `reviewer_supplied` with who/when/why, feeding the create-draft payload. This is the **missing entry point** from Section 1.3.
3. **Acknowledge optional defaults**: each defaulted loss/soiling row shows "Default 0% applied — confirm or override," so a 0%-loss assumption is never invisible.

### F.6 Honesty rules (must hold)

- Never render a defaulted/absent value as a fact-derived value.
- Never show `0` where the true state is "unknown/defaulted" — mirror the existing telemetry honesty contract (null ≠ 0).
- Every reviewer-entered value is visually distinct from a document-extracted value and carries provenance.

---

## G. Normalization UX design — comparing the five options

How users should resolve values like `"340 Wp"` / `"66 kWac"`.

### Option 1 — Normalize during **parsing** (parser emits `numeric_value` + `unit`; fact stores `normalized_value` + `display_value`)

- **Pros:** cleanest model; lineage stage 4 becomes real and persistent; every downstream consumer gets a number; future extractions are correct by construction.
- **Cons:** highest engineering effort (parser + schema + fact-model changes); does **not** retroactively fix existing `"340 Wp"` facts; risk of the parser guessing units.
- **Auditability:** excellent (raw + normalized both stored). **User effort:** low after build. **Engineering risk:** high. **Impact on existing facts:** none retroactively. **Preserves history:** yes.

### Option 2 — Normalize during **acceptance** (Data Room shows raw value, asks reviewer to confirm numeric + unit)

- **Pros:** human in the loop exactly where provenance is already recorded; produces an auditable accepted value with both raw and numeric; fixes new and (on re-acceptance) existing values; no silent guessing.
- **Cons:** adds a confirmation step to acceptance; needs a place to store `numeric_value`/`unit` alongside the accepted value.
- **Auditability:** excellent. **User effort:** low/medium. **Engineering risk:** medium. **Impact on existing facts:** addressed on next acceptance. **Preserves history:** yes (raw retained).

### Option 3 — Normalize during **promotion** (promotion blocks / requires normalization confirmation before active fact)

- **Pros:** guarantees every *active* fact is numeric; strong gate right before the value becomes authoritative.
- **Cons:** promotion is currently a clean state transition; injecting a data-entry step there is heavier; doesn't help values already promoted (like the user's).
- **Auditability:** good. **User effort:** medium. **Engineering risk:** medium. **Impact on existing facts:** none retroactively (already promoted). **Preserves history:** yes.

### Option 4 — Normalize during **baseline readiness** (active fact stays raw; readiness asks for a confirmed normalized baseline input)

- **Pros:** **smallest blast radius** — no change to parsing/acceptance/promotion or to historical facts; the raw fact is preserved untouched; the normalized value is a baseline-scoped, reviewer-confirmed input with its own provenance; fixes the user's *current* stuck site immediately.
- **Cons:** the active fact remains non-numeric (reconciliation must show `value_present_but_not_numeric`); normalization is re-confirmed per baseline build rather than once.
- **Auditability:** excellent (normalization recorded in `model_parameters_json.field_sources`). **User effort:** low. **Engineering risk:** low. **Impact on existing facts:** zero. **Preserves history:** yes.

### Option 5 — **No normalization**; require exact numeric values from parser/reviewer (status quo + override)

- **Pros:** zero new normalization machinery; absolute "never guess."
- **Cons:** every text-with-unit value requires a manual fact override to a bare number, *losing* the original unit context unless the reviewer is careful; poor UX; doesn't scale.
- **Auditability:** ok. **User effort:** high. **Engineering risk:** none. **Impact on existing facts:** manual. **Preserves history:** weak (override may discard the unit).

### G.1 Recommendation

**Phase 1 = Option 4** (normalize at baseline readiness with explicit confirm), because it unblocks the user's site immediately with the smallest, safest change and **zero mutation of historical facts** — directly honoring the durable invariant. **Phase 2 = Option 2** (acceptance-time confirm) as the durable home, so normalized values become first-class on the accepted value and feed everything downstream. **Option 1** is the long-term ideal once datasheet document types exist. **Never** auto-normalize inside `_coerce_number` (silent), and **never** auto-convert units (W↔kW) without explicit per-value confirmation.

Decision rule the UX must encode:

- **Safe (auto-suggest, one-click confirm):** unit token matches the field's expected unit (`Wp`→W for module, `kWac`→kW for inverter). Strip token, keep number.
- **Requires conversion (explicit confirm, show before/after):** unit present but differs from expected (`Wac`→kW). Apply a *declared* conversion factor, show it.
- **Block (cannot proceed):** missing unit on a W-vs-kW-ambiguous field, ambiguous unit, or implausible magnitude (`_unit_warnings` trips) → ask user, never assume.

---

## H. Design-estimate points audit (0/12)

### H.1 Why it is 0/12

`baseline_points_service.py` builds points **only** from monthly/annual production `project_facts` (`MONTHLY_PRODUCTION_FIELDS`, `ANNUAL_PRODUCTION_FIELD`). `0/12 months present` means **no monthly points are currently represented/evaluable** for the site. The most common cause is that no monthly production facts are active/promoted, but it can also arise when no design-estimate baseline exists yet, or when monthly facts exist but parse as non-numeric. The generator is deliberately conservative: it **never distributes an annual total into months** and **never fabricates** points (`:14-15`). So even a present annual fact yields 0 *monthly* points.

### H.2 Trace checklist (what to verify for the specific site)

| Question | Where to look | Likely state for a 0/12 site |
|---|---|---|
| Do monthly production values exist in a PVsyst/design doc? | PVsyst is extraction-covered (monthly fields exist) | Possibly yes in a document, but… |
| Are they parsed → accepted → promoted to active facts? | `project_facts` for `*_estimated_production_year_1` | **No** (the gap) |
| Does annual production exist? | `estimated_production_year_1` fact | Maybe, but doesn't create monthly points |
| Does a design-estimate baseline header exist? | `telemetry_expected_baselines` `baseline_type='design_estimate'` | Likely **no** |
| Was generate-design-points run? | points rows | **No** |
| Blocked by missing/non-numeric values? | same `_coerce_number` numeric rule applies; assumes kWh `unit_verified=false` | Possibly, if production values carry units |

### H.3 Required user flow (design)

```
Upload PVsyst / design-estimate document
  → Extract monthly + annual production (already covered)
  → Accept / promote the production facts (Data Room)
  → Create the design-estimate baseline (separate from the weather-adjusted draft)
  → Generate design-estimate points
  → Compare design-estimate vs actual vs weather-adjusted expected as THREE distinct series
```

**Critical clarification for UX:** design-estimate points and the weather-adjusted draft are **two independent "expected" notions** (PVsyst contractual forecast vs weather-adjusted physics). The Baseline Readiness panel currently conflates "not ready" across both; the redesign must show them as separate readiness tracks so a user understands that fixing the nine physics inputs does **not** populate the 12 monthly points, and vice-versa.

---

## I. PTO / pre-PTO behavior audit

### I.1 Current behavior (confirmed)

- `pto_date` is a reviewer-supplied column on the baseline (`models/telemetry_expected.py:193`; set at create, `baseline_from_facts_service.py:357-360`).
- PTO absence is **not** a draft blocker — only a warning (`baseline_from_facts_service.py:357-365`).
- In the calc: **`pto_date is None` ⇒ every bucket `pre_pto`, expected = NULL** (`expected_service.py:315-328`); a bucket before PTO ⇒ `pre_pto`, expected = NULL (`:330-344`). So missing PTO suppresses the **entire** expected curve, not merely the pre-PTO portion.

### I.2 Source / provenance audit

| Question | Finding |
|---|---|
| Where should PTO come from? | Utility/interconnection approval or PTO letter; extractable from **EPC agreement** today |
| Does PTO exist in documents? | Yes — EPC extraction covers PTO |
| Accepted/promoted? | Not wired as a baseline-driving fact; reviewer-supplied on create only |
| Protected in Overview? | PTO/`permission_to_operate` appears in the protected Overview surface (per `protected-baseline-saql-guard` memory) and legacy SAFL map |
| In Reconciliation? | **No catalog row** (SAFL display-only map only) |

### I.3 Recommended final behavior

- **Draft baseline:** **can** be created without PTO (keep current — physics constants are the gating inputs). Show `pre_pto_expected_suppressed` clearly.
- **Active baseline:** **require PTO before activation** (or require an explicit, audited "activate without PTO — expected intentionally suppressed" acknowledgement). Activating a baseline whose expected silently computes to NULL everywhere is a footgun.
- **Expected chart before PTO:** render an explicit "Expected suppressed until PTO (DATE)" empty state — never 0, never a flat line.
- **User-facing label:** "Permission to Operate (PTO) — required for expected production."
- **Wiring:** add PTO as a reconciliation/readiness row sourced from the EPC fact (with reviewer override), so the value the user already has in a document can flow in rather than being re-typed.

---

## J. Historical analytics & baseline activation caution

This audit makes **no** activation changes; it documents the guardrails the eventual activation must respect (the durable platform invariant).

- **New active baseline must not silently rewrite prior periods.** Activation creates a *new* lineage; it must not retroactively change historical expected/comparative values that were computed under a previous baseline.
- **Historical O&M analytics must preserve which baseline/facts/weather were active at the time.** Each historical period's expected should remain attributable to the baseline version (and its `model_parameters_json` provenance) that produced it. The single-active partial unique index gives a *current* pointer, not a *temporal* one — period-effective selection (Phase 9) is required before any backfill.
- **Any backfill/recalculation must be explicit, period-scoped, and audited.** No implicit recompute on activate. A recalculation is an operator action with a stated window and an audit record.
- **Upstream source changes must mark dependent state stale** (the existing promotion freshness guard is the precedent): if a `project_fact` that fed a baseline changes, the baseline/expected derived from it must be flagged stale and require re-review — never silently kept.

---

## K. Implementation recommendation (phased)

Each phase is independently shippable and ordered by risk-adjusted value. **All phases preserve the lineage and the durable invariant; none auto-normalizes or auto-promotes.**

### Phase 1 — Baseline-readiness source trace + actionable blocker details
- **Goal:** make the panel explain *why* each field is unusable and *what to do next* (Section F), including surfacing the five reviewer-required constants as explicit "needs input" rows.
- **Risk:** Low (read + presentation; the evaluator already computes most of this).
- **Backend:** `baseline_from_facts_service.py` (expose per-field reason/source-status/required-action in the readiness response), `schema/telemetry_v2.py` (`ReadinessFromFactsResponse` additive fields).
- **Frontend:** Baseline Readiness panel component (additive columns/affordances).
- **Tests:** readiness response includes per-field status + action; five reviewer constants reported as `reviewer_supplied_input_needed`.
- **Non-goals:** no normalization, no create/activate changes.

### Phase 2 — Unit/normalization guard for numeric baseline inputs (Option 4)
- **Goal:** allow a reviewer to confirm a normalized baseline input for a text-with-unit fact, recorded in `model_parameters_json` provenance; raw fact untouched.
- **Risk:** Low–Medium.
- **Backend:** `baseline_from_facts_service.py` (accept confirmed normalized values + record provenance; keep `_coerce_number` strict; add a *declared* safe-unit map, never auto-convert).
- **Frontend:** "Normalize / confirm unit" affordance.
- **Tests:** Section L #1, #2; conversion case requires explicit confirm; unsafe case blocks.
- **Non-goals:** no parser change, no fact mutation.

### Phase 3 — Data Room / acceptance normalization UX (Option 2)
- **Goal:** capture numeric + unit at acceptance so normalized values become first-class on the accepted value and downstream facts.
- **Risk:** Medium (touches acceptance write path + a place to store numeric/unit).
- **Backend:** acceptance services (`project_facts_service.py`, document-key acceptance), additive storage of numeric/unit alongside raw.
- **Frontend:** Data Room acceptance dialog.
- **Tests:** accepted value stores raw + numeric + unit; existing facts unaffected until re-accepted.
- **Non-goals:** no silent normalization; no retroactive rewrite.

### Phase 4 — Reconciliation indicators for non-numeric / reviewer-needed / defaulted inputs
- **Goal:** add the recommended statuses (Section E.3) and additive catalog rows for the five constants + PTO + losses/soiling (display/status only).
- **Risk:** Low–Medium (read-only service + static catalog).
- **Backend:** `reconciliation_catalog.py` (additive rows), `reconciliation_service.py` (new status derivation; still zero writes).
- **Frontend:** `ReconciliationTable.tsx` / `StatusCell` (new chips/labels).
- **Tests:** Section L #1, #2 surfaced in reconciliation; required-but-missing constants show `blocks_baseline`.
- **Non-goals:** no normalization/promotion in the read-only service.

### Phase 5 — Create-draft-from-facts blocker links/actions
- **Goal:** wire the panel's "Add reviewer-supplied baseline input" and "Normalize" actions into the existing create-draft endpoint; deep-link "Open Data Room" for acceptance/promotion gaps.
- **Risk:** Low (the endpoint already accepts reviewer values).
- **Backend:** endpoint validation messages.
- **Frontend:** action wiring.
- **Tests:** create returns 422 `review_required` with structured per-field gaps; success path with reviewer constants.
- **Non-goals:** no auto-create on load.

### Phase 6 — Design-estimate points flow repair
- **Goal:** make the design-estimate track explicit and separate (Section H): show monthly/annual production readiness, "Create design-estimate baseline," and "Generate points" as discrete steps.
- **Risk:** Medium.
- **Backend:** `baseline_points_service.py` surfacing (keep never-distribute, never-fabricate; surface `unit_verified=false`).
- **Frontend:** separate design-estimate readiness section.
- **Tests:** 0/12 explained; annual-only does not fabricate months; kWh assumption labeled unverified.
- **Non-goals:** no annual→monthly distribution.

### Phase 7 — PTO readiness behavior
- **Goal:** implement Section I — PTO row sourced from EPC fact, draft allowed without PTO, activation requires PTO (or audited override), explicit pre-PTO empty state.
- **Risk:** Medium (touches activation gate).
- **Backend:** activation validation; PTO reconciliation row.
- **Frontend:** PTO blocker row + chart empty state.
- **Tests:** PTO-None ⇒ all buckets `pre_pto`; activation blocked/acknowledged without PTO.
- **Non-goals:** no change to the pre-PTO suppression math.

### Phase 8 — Optional defaults labeling
- **Goal:** Section 1.2 — structured `default_applied_optional_input` indicator for losses/soiling; never present a default as a fact.
- **Risk:** Low.
- **Backend:** readiness/reconciliation flags.
- **Frontend:** "Default applied" chips.
- **Tests:** Section L #4, #5.
- **Non-goals:** no change to default *values* (0% / 1.0).

### Phase 9 — Period-effective baseline selection (later)
- **Goal:** Section J — temporal baseline attribution so activation/backfill never silently rewrites history.
- **Risk:** High (data-model + read-path).
- **Backend:** baseline effective-period model + expected read-path selection.
- **Frontend:** historical baseline attribution display.
- **Tests:** historical periods retain their original baseline; backfill is explicit/period-scoped/audited.
- **Non-goals:** no implicit recompute on activate.

---

## L. Tests to design

Designed test cases (specifications, not implementations). Backend tests follow the ilios-server harness (own DB via `test_db_name`, `monkeypatch` not pytest-mock).

### L.1 Non-numeric active fact → `value_present_but_not_numeric` (`module_wattage="340 Wp"`)
- **Arrange:** site with an active `module_wattage` fact whose value is `{"v": "340 Wp"}`.
- **Assert (readiness/reconciliation):** field status is `value_present_but_not_numeric` (not `active_fact`, not bare `missing`); `current_value="340 Wp"`; `required_action="Normalize / confirm unit"`; `blocking_level=blocks_baseline`.
- **Assert (calc safety):** `_coerce_number("340 Wp") is None`; draft create returns not-ready listing `module_wattage`.

### L.2 Non-numeric active fact (`inverter_wattage="66 kWac"`)
- Same as L.1 for `inverter_wattage`; assert the safe-normalization suggestion is `66` (kW) and that confirmation is required before it is used; assert no auto-conversion occurs.

### L.3 Missing thermal coefficient blocks the draft
- **Arrange:** all four fact-backed physics present and numeric; no reviewer values supplied.
- **Assert:** `evaluate_readiness().ready is False` and `thermal_coefficient_pct` (plus the other four reviewer constants) appear as `reviewer_supplied_input_needed` / `missing` with `blocks_baseline`; `create_draft_from_facts` without them returns not-ready (422 `review_required`).

### L.4 Optional losses default to 0 only when explicitly labeled as default
- **Arrange:** ready physics + reviewer constants; omit `dc_loss_pct`/`ac_loss_pct`/`medium_voltage_loss_pct`/`mv_line_loss_pct`.
- **Assert:** readiness emits a `default_applied_optional_input` indicator for each (not a fabricated value); created draft's `model_parameters_json.warnings` records the 0%-default application; the field is **not** shown as a document-sourced value.

### L.5 Missing soiling defaults to 1.0 only when explicitly labeled
- **Arrange:** as L.4 but omit `soiling_factor`.
- **Assert:** `default_applied_optional_input` for `soiling_factor` with value `1.0` labeled "no-soiling default"; never presented as fact-derived.

### L.6 (Recommended additional) PTO-None suppresses the entire expected curve
- **Arrange:** active baseline with `pto_date=None`, rollups present with valid irradiance + cell temp.
- **Assert:** every `ExpectedBucket.status == pre_pto`, `expected_power_kw is None`; the expected state surfaces as `pre_pto` (never 0).

### L.7 (Recommended additional) Safe vs unsafe normalization decision rule
- **Assert:** `"340 Wp"` (module, expects W) → safe strip → `340`; `"66 kWac"` (inverter, expects kW) → safe strip → `66`; `"66000 Wac"` (inverter) → flagged as requiring W→kW conversion confirmation; unit-less ambiguous value → blocked, never assumed.

### L.8 (Recommended additional) Raw fact is never mutated by normalization (invariant)
- **Assert:** after a reviewer confirms a normalized baseline input, the underlying active `project_fact.value` is unchanged (`{"v": "340 Wp"}`); the normalization is recorded only in baseline provenance — proving history is preserved.

---

## Appendix — code reference index

| Concern | Location |
|---|---|
| Required physics set (9) | `app/services/telemetry/expected_service.py:81-91` |
| Optional defaults (losses 0%, soiling 1.0, pto None) | `app/services/telemetry/expected_service.py:137-142` |
| Physics formula (W vs kW units; AC clip) | `app/services/telemetry/expected_service.py:271-306` |
| PTO suppression (None ⇒ all pre_pto; before-PTO) | `app/services/telemetry/expected_service.py:315-344` |
| `from_baseline` raises on missing required | `app/services/telemetry/expected_service.py:145-161` |
| Fact→column map (4 fact-backed fields) | `app/services/telemetry/baseline_from_facts_service.py:51-56` |
| Reviewer-required set (5 constants) | `app/services/telemetry/baseline_from_facts_service.py:70-72` |
| Optional loss fields | `app/services/telemetry/baseline_from_facts_service.py:77-82` |
| `_coerce_number` (float-only; rejects unit) | `app/services/telemetry/baseline_from_facts_service.py:162-179` |
| `_unit_warnings` (warn, never convert) | `app/services/telemetry/baseline_from_facts_service.py:216-229` |
| Evaluator: non-numeric → missing + warning | `app/services/telemetry/baseline_from_facts_service.py:258-270` |
| Evaluator: reviewer-required handling | `app/services/telemetry/baseline_from_facts_service.py:312-318` |
| Evaluator: optional defaults + warnings | `app/services/telemetry/baseline_from_facts_service.py:325-365` |
| `evaluate_readiness` (facts-only, reviewer=None) | `app/services/telemetry/baseline_from_facts_service.py:464-476` |
| `ProjectFact.value` JSONB envelope | `app/models/project_facts.py:43` |
| Reconciliation status ladder + blocking levels | `app/services/due_diligence/reconciliation_service.py:89-97, 604-655` |
| Reconciliation catalog (4 physics required; design-estimate points; SAFL display map) | `app/static/reconciliation_catalog.py:125-208` |
| Design-estimate point fields (monthly/annual) | `app/services/telemetry/baseline_points_service.py:68-82` |
| Extraction config (PVsyst/EPC coverage) | `configs/ai_parsing_config.json` |
| `pto_date` baseline column | `app/models/telemetry_expected.py:193` |

---

*End of audit. No code, schema, or data was modified in producing this document. All recommendations are deferred to an approved follow-up implementation sprint.*
