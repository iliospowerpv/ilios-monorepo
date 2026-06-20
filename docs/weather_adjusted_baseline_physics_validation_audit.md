# Weather-Adjusted Baseline Physics Validation Audit

**Type:** Audit & design sprint (no implementation)
**Status:** Complete — design recommendations only. No code, migrations, endpoints, UI, or data was changed. No baseline was created, edited, approved, activated, or superseded; no `project_facts`, accepted values, or historical O&M were touched.
**Scope of subject system:** The weather-adjusted expected-performance physics (`expected_service.py`), the promoted-facts → draft-baseline bridge (`baseline_from_facts_service.py`), the baseline lifecycle CRUD (`crud/telemetry_expected.py`), and the three lifecycle endpoints (`routers/telemetry/v2.py`).
**Date:** 2026-06-20

---

## 0. How to read this document

This audit answers one strategic question:

> The weather-adjusted expected curve is driven by a handful of physics constants stored on the active baseline. **Which of those constants can hold values that are physically impossible or implausible, how would we detect them, where in the draft → approve → activate lifecycle should we stop a bad value, and what should the system do when an *already-active* baseline is found to be invalid** — all without changing the expected formula, mutating any existing baseline (especially Site 4's active baseline id 3), or fabricating values.

It is organized to the seven requested deliverables:

| § | Deliverable |
|---|-------------|
| 2 | Field validation matrix (unit, plausible / warning / hard-invalid bounds) |
| 3 | Thermal-coefficient semantics + recommended UI wording |
| 4 | Site 4 baseline #3 read-only assessment with provenance + per-field verdict |
| 5 | Approval / activation gate design (pre-draft, pre-approval, pre-activation) |
| 6 | Replacement-baseline lifecycle (corrections create a NEW baseline) |
| 7 | O&M behavior when the active baseline is invalid |
| 8 | Test plan + phased roadmap |

Every factual claim is grounded in a code citation of the form `path:line`. Every numeric bound in the validation matrix is a **recommended design value**, not something enforced today (Section 2.1 states exactly what is enforced now).

### Constraints honored by this audit

This is a **read-only** audit. It made **no** production code changes. Specifically it did NOT, and any future implementation following it must NOT:

- mutate the active baseline **id 3**, any `project_facts`, any accepted document value, or historical O&M data;
- auto-backfill or auto-correct any stored value;
- change the expected physics formula, telemetry ingestion, the `WeatherResolver`, device eligibility, or period-effective baseline selection;
- use `SiteAdditionalFieldList` (SAFL) as a V2 baseline source;
- reintroduce any BigQuery / Firestore / legacy-telemetry path.

It preserves the existing lifecycle (`draft → in_review → approved → active → superseded`) and the rule that **a correction is a NEW replacement baseline, never an in-place edit of an active one**.

---

## 1. Executive summary

### 1.1 One stored constant can silently corrupt the entire expected curve

The weather-adjusted physics requires nine fields (`expected_service.py:82-92`). The per-bucket calc multiplies a chain of derate factors (`expected_service.py:296-334`); two of them are unbounded and sign-sensitive:

- **`temperature_factor = 1 + (thermal_coefficient_pct / 100) * (cell_°C − 25)`** (`expected_service.py:308, 327-329`). A correct PV power temperature coefficient is a small **negative** number, ≈ −0.35 %/°C (the datasheet field's own example is `-0.35`, `module.py:32`). If the stored value is positive, or off by orders of magnitude, this factor explodes: positive in heat (expected pinned to AC nameplate — gross over-expectation) and **negative in cold** (negative expected power and energy, since the only clip is an *upper* clip to AC nameplate, `expected_service.py:333-334` — there is **no lower clamp**).
- **The voltage-drop factors** `1 − loss%/100` (`expected_service.py:302-305`): if the loss percentages summed past 100 they would drive the derate negative as well.

So a single bad constant produces a confidently-rendered but completely wrong expected line, with **no current detection** anywhere in the pipeline.

### 1.2 Today almost nothing validates these values

The only checks that exist:

1. **Required-present + numeric** at draft creation. `_coerce_number` returns `None` for a non-numeric fact and the field is reported missing, never guessed (`baseline_from_facts_service.py:301-318`); `evaluate_readiness` reports the full required set (`baseline_from_facts_service.py:941-953`); the create endpoint returns `422 review_required` when anything required is missing (`routers/telemetry/v2.py:2854-2881`).
2. **Two free-text unit hints** — `module_wattage < 50` ("looks like kW") and `inverter_wattage > 1000` ("looks like W") — emitted as non-blocking warnings only (`baseline_from_facts_service.py:355-368`).
3. **Missing-required guard at compute time** — `BaselineParams.from_baseline` raises `ValueError` if a required field is `None` (`expected_service.py:153-162`).

There is **no plausibility/range validation, no sign check, no cross-field check, and no compute smoke-test** at draft, approval, activation, or read. A value like `thermal_coefficient_pct = 350` passes every existing gate.

### 1.3 Site 4's active baseline is the live proof

Active baseline **id 3** (Site 4 / company 6) is structurally healthy — correct lifecycle, full provenance, fact-backed equipment — but stores **`thermal_coefficient_pct = 350.0`** (Section 4). That is the datasheet number off by ~1000× **and** sign-flipped (correct ≈ −0.35). It alone makes every weather-adjusted expected value for Site 4 untrustworthy. It is reviewer-supplied (Section 4.2), i.e. a data-entry error that no gate caught. A secondary warning value (`power_tolerance_min_pct = 5.0`) and several optimistic defaults (no losses, no soiling) compound it.

### 1.4 The headline recommendation

A small, additive, **read-only-respecting** validation layer:

1. A **validation matrix module** (Section 2) classifying every physics field as `plausible / warning / hard_invalid`, plus a cheap **compute smoke-test** that rejects a baseline whose physics yields negative or non-finite expected, or an impossible derate factor, at probe temperatures (ordinary AC-nameplate clipping is healthy and is *not* treated as a failure).
2. **Wire it as fail-closed at activation first** (Section 5.3) — the highest-value, lowest-risk gate: it cannot touch any existing active row and would have blocked baseline #3. Then add a pre-approval gate and non-blocking draft warnings.
3. A **read-time `baseline_invalid` state** (Section 7) so the O&M/expected surface stops rendering a corrupt curve and prompts for a replacement — **without auto-deactivating** the bad baseline.
4. Fix Site 4 the only legal way: **create a corrected NEW replacement baseline and activate it** (Section 6) — never edit #3.

No value is ever auto-corrected, auto-converted, or silently clamped; the system surfaces the defect honestly and asks a human to create a replacement.

---

## 2. Deliverable 1 — Field validation matrix

### 2.1 What is enforced today (baseline)

| Check | Where | Behavior |
|-------|-------|----------|
| Required field present | `expected_service.py:82-92`, `baseline_from_facts_service.py:941-953` | Missing → `422 review_required`, no row created |
| Value numeric | `baseline_from_facts_service.py:301-318` | Non-numeric → treated as **missing** (never guessed) |
| `module_wattage < 50` / `inverter_wattage > 1000` | `baseline_from_facts_service.py:355-368` | Free-text **warning only**, non-blocking |
| Loss sign | `crud/telemetry_expected.py:89-91` (`_abs_or_none`) | Losses normalized to positive % at create |
| Required present at compute | `expected_service.py:153-162` | Missing → `ValueError` (curve unavailable) |

There is **no** range, sign, magnitude, cross-field, or compute-output validation. Everything below in §2.2 is a **design proposal**.

### 2.2 Proposed validation matrix (recommended bounds)

Semantics first — these are non-obvious and drive the bounds:

- All `*_pct` columns are stored **as percent** and divided by 100 **exactly once** in the calc (`expected_service.py:125-126, 302-310`). The stored value is the datasheet number itself (e.g. `-0.35`, `97`), never a fraction and never ×100.
- **`inverter_wattage` is in kW, not W** — `ac_nameplate_kw = inverter_wattage * inverter_quantity` with no `/1000` (`expected_service.py:300`). `module_wattage` *is* in W (`dc_nameplate_kw = module_wattage * module_quantity / 1000`, `expected_service.py:299`). This W-vs-kW asymmetry is the single biggest unit hazard.
- Loss percents are subtracted as `1 − loss/100`; soiling is a multiplier defaulting to `1.0`; missing losses default to `0.0` (`expected_service.py:138-142, 178-182`).

| Field | Unit | Plausible (no flag) | Warning (allow + flag) | Hard-invalid (block) | Rationale / citation |
|-------|------|---------------------|------------------------|----------------------|----------------------|
| `module_wattage` | W (per module) | 250 – 900 | 50–250 or 900–1500 | ≤ 0, non-numeric, or < 50 (kW-vs-W) | Existing kW hint `…:358`; STC module class |
| `module_quantity` | count | 1 – 500,000 | > 500,000 | ≤ 0 | DC nameplate sanity `…:299` |
| `inverter_wattage` | **kW** (per inverter) | 1 – 1,000 | 1,000–10,000 (large central inverter **or** W-vs-kW slip — verify) or < 1 | ≤ 0 or > 10,000 | kW semantics `…:300`; existing hint `…:363` |
| `inverter_quantity` | count | 1 – 50,000 | > 50,000 | ≤ 0 | AC nameplate sanity `…:300` |
| `thermal_coefficient_pct` | %/°C | −0.50 … −0.20 | −0.55…−0.50, −0.20…−0.05, or per-unit-looking (|v|<0.05) | **≥ 0** (wrong sign) or **|v| > 1** (magnitude) | Datasheet example −0.35 `module.py:32`; calc `…:308, 327-329` |
| `power_tolerance_min_pct` | % | −5 … 0 | 0 … +5 (likely the max side / wrong sign) | |v| > 10 | Datasheet `min_power_tolerance` is `le=0` `module.py:40` |
| `year_1_degradation_pct` | % | 1.0 … 3.0 | 0–1 or 3–5 | < 0 or > 10 | Datasheet example 2 `module.py:33` |
| `annual_degradation_pct` | % | 0.3 … 1.0 | 0–0.3 or 1.0–2.0 | < 0 or > 5 | Datasheet example 0.54 `module.py:34` |
| `cec_efficiency_pct` | % | 94 … 99.5 | 90–94 or 99.5–100 | ≤ 50, > 100 | Inverter efficiency `…:307` |
| `soiling_factor` | fraction (≤1) | 0.90 … 1.00 | 0.80–0.90 | ≤ 0 or > 1.05 (gain, not loss) | Multiplier `…:318`; default 1.0 `…:138` |
| `dc_loss_pct` | % | 0 … 8 | 8 … 20 | < 0 (post-abs impossible) or ≥ 100 | `1 − dc/100` `…:302`; default 0 |
| `ac_loss_pct` | % | 0 … 3 | 3 … 10 | ≥ 100 | `…:303-305`; default 0 |
| `medium_voltage_loss_pct` | % | 0 … 3 | 3 … 10 | ≥ 100 | `…:303-305`; default 0 |
| `mv_line_loss_pct` | % | 0 … 3 | 3 … 10 | ≥ 100 | `…:303-305`; default 0 |
| `pto_date` | date | a past or near-future real date | far-future (suppresses curve until then) | none (`None` is a draft-readiness blocker for WAM, not a value error) | pre-PTO suppression `…:343-372`; PTO required per readiness |

### 2.3 Cross-field and compute-output checks

Single-field bounds are not enough; two derived checks catch the rest:

1. **DC/AC ratio** `= (module_wattage·module_quantity/1000) / (inverter_wattage·inverter_quantity)`. Plausible **1.0 – 1.5**; warning 1.5–2.0 or < 1.0; hard-invalid > 3 or ≤ 0. (Site 4: 646/462 = **1.40**, plausible.)
2. **AC-side loss sum** `ac_loss_pct + medium_voltage_loss_pct + mv_line_loss_pct` (`expected_service.py:303-305`). Warning > 15; hard-invalid ≥ 100 (would invert the AC drop).
3. **Compute smoke-test (the strongest guard).** Build `BaselineParams.from_baseline` and evaluate `_expected_power_kw` at a small fixed probe set, e.g. (irradiance 1000 W/m², cell 5 °C) and (1000 W/m², 45 °C). **Hard-invalid if** expected is **< 0** or **non-finite** (NaN/Inf) at any probe, or if any intermediate derate factor is impossible — `temperature_factor ≤ 0`, or any voltage-drop factor `≤ 0` (the loss-sum guard, §2.3.2). **Do NOT treat ordinary AC-nameplate clipping as invalid:** clipping is normal and expected for DC/AC ratios ≈ 1.2–1.5 (Site 4's healthy 1.40 ratio legitimately clips near 1000 W/m² even with a correct thermal coefficient), so saturation at the AC nameplate is *not* a defect signal. This check still flags baseline #3 — its `350` value drives `temperature_factor = 1 + 3.5·(5−25) = −69` (≤ 0) and a negative expected at the 5 °C probe — without false-flagging healthy clipping systems. It must call a **read-only copy** of the formula or the existing pure `_expected_power_kw` with no DB writes — it must not change the formula.

### 2.4 Design constraints on the matrix

- The matrix is an **additive, standalone module** (proposed `app/services/telemetry/baseline_physics_validation.py`). It does not change `expected_service.py`'s math; it only *reads* values and classifies them.
- It **never auto-corrects** and **never auto-converts units** (consistent with `baseline_from_facts_service.py`'s existing never-guess contract).
- Bounds live in one place as named constants so they are reviewable and adjustable without touching enforcement sites.
- `warning` never blocks; only `hard_invalid` blocks, and only at the gates chosen in Section 5.

---

## 3. Deliverable 2 — Thermal-coefficient semantics + UI wording

### 3.1 What the field is

`thermal_coefficient_pct` is the **module maximum-power temperature coefficient (γ_Pmax)** — how much DC power changes per °C of cell temperature away from the 25 °C STC reference. For crystalline-silicon PV it is **always negative** (power falls as the cell heats) and typically **−0.50 … −0.20 %/°C**. The datasheet schema names it "Thermal Coefficient of Power (%)" with example **−0.35** (`module.py:32, 41`).

### 3.2 How the calc consumes it (the exact contract)

```
thermal_coefficient = thermal_coefficient_pct / 100        # expected_service.py:308
temperature_factor  = 1 + thermal_coefficient * (cell_°C − 25)   # :327-329
```

So the **stored column must hold the datasheet %/°C number directly** — e.g. `-0.35`. At a 45 °C cell that gives `1 + (−0.0035)(20) = 0.93` (a 7% hot-weather derate); at 5 °C, `1.07` (a cold-weather gain). Correct and bounded.

### 3.3 The four common data-entry errors (and what each does)

| Entry mistake | Stored | Effective per-°C | Result |
|---------------|--------|------------------|--------|
| Correct | `-0.35` | −0.0035 | ✅ ~7% derate at 45 °C |
| Sign dropped | `0.35` | +0.0035 | ❌ power *rises* with heat — backwards |
| Per-unit fraction | `-0.0035` | −0.000035 | ⚠️ temperature effect ~nil (100× too small) |
| ×100 / basis-point | `-35` or `350` | −0.35 or **+3.5** | ❌ massive; **+3.5** ⇒ negative expected in cold, AC-pinned in heat |

Site 4's `350` is the worst case: **positive and ~1000× too large** (Section 4).

### 3.4 Recommended UI wording (create-draft / reviewer constant input)

- **Label:** "Module power temperature coefficient (γ_Pmax)"
- **Unit suffix:** "% per °C"
- **Helper text:** "From the module datasheet ('Temperature Coefficient of Pmax'). Enter the datasheet number directly — usually between **−0.50 and −0.20**, and **negative** (power drops as the panel heats). Example: **−0.35**."
- **Inline validation (mirrors the matrix):**
  - Block if `≥ 0`: "Must be negative — PV power decreases as temperature rises."
  - Block if `|value| > 1`: "Out of range for a %/°C coefficient — check you didn't multiply by 100 (enter −0.35, not −35 or 350)."
  - Warn if `|value| < 0.05`: "This looks like a per-unit fraction — datasheet values are in %/°C, e.g. −0.35."
  - Warn if outside −0.50…−0.20 but otherwise valid.
- **Live derived preview** beside the input: "At a 45 °C cell, this derates expected power by **N%**" — recomputed from the entered value so a wrong magnitude is visible immediately (a +3.5 entry would show an absurd preview).

These are presentation guards; the authoritative block is server-side (Section 5).

---

## 4. Deliverable 3 — Site 4 baseline #3 read-only assessment

> Read-only. Nothing below was changed. Per the hard constraints, baseline id 3 must not be edited — the remedy is a replacement (Section 6).

### 4.1 Header & lifecycle (all healthy)

| Attribute | Value |
|-----------|-------|
| id / site / company | 3 / 4 / 6 |
| name / type | "Diligence facts baseline v1" / `weather_adjusted_model` |
| status | **active** (correct: single active per site+type, `crud/telemetry_expected.py:120-133`) |
| version | 1 |
| `active_from` / `active_to` | 2026-05-11 00:00:00 / NULL |
| `pto_date` | 2026-05-11 |
| timezone | America/New_York |
| reviewed / approved | user 1 @ 2026-06-19 19:41:46 |
| created | user 1 @ 2026-06-19 19:40:56 |
| source | `diligence_ai_parse`, document 912, primary fact 114 |

`active_from` equals the PTO date — exactly the first-activation backdate rule (`crud/telemetry_expected.py:33-52, 328`): the first active WAM baseline carrying a PTO is effective from PTO so the curve covers pre-activation telemetry. Lifecycle is **correct**.

### 4.2 Provenance of the physics values

From `model_parameters_json.field_sources`:

- **Equipment (fact-backed, document 912):** `module_wattage` 340 W (normalized `"340 Wp"` → 340, unit_strip, confirmed by user 1), `module_quantity` 1900 (fact 115), `inverter_wattage` 66 kW (normalized `"66 kWac"` → 66, fact 118), `inverter_quantity` 7 (fact 119). Normalizations are recorded and auditable.
- **Reviewer-supplied (no fact source):** `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct` — all flagged `source: reviewer_supplied`.
- **Defaulted (absent):** all four loss percents and `soiling_factor` are NULL; `model_parameters_json.warnings` already records "calc applies a 0% default for these losses" and "applies the 1.0 (no-soiling) default."

**Conclusion:** the corrupt value is **reviewer-supplied**, a manual data-entry error — not a parsing or fact problem. No existing gate examined it.

### 4.3 Per-field verdict (against the Section 2 matrix)

| Field | Stored | Verdict | Note |
|-------|--------|---------|------|
| `module_wattage` | 340 W | ✅ plausible | |
| `module_quantity` | 1900 | ✅ plausible | |
| `inverter_wattage` | 66 kW | ✅ plausible | kW semantics correct |
| `inverter_quantity` | 7 | ✅ plausible | |
| **`thermal_coefficient_pct`** | **350.0** | **❌ HARD-INVALID** | Positive **and** ~1000× too large; correct ≈ −0.35. Drives `temperature_factor = 1 + 3.5·(cell_°C−25)` → negative expected in cold, AC-pinned in heat |
| `power_tolerance_min_pct` | 5.0 | ⚠️ warning | Datasheet "min" tolerance is `le=0` (`module.py:40`); +5 is the wrong side → ~5% optimistic |
| `year_1_degradation_pct` | 2.5 | ✅ plausible | |
| `annual_degradation_pct` | 0.73 | ✅ plausible | |
| `cec_efficiency_pct` | 97.0 | ✅ plausible | |
| `soiling_factor` | NULL | ⚠️ default 1.0 | optimistic (no soiling) |
| `dc/ac/mv/mv-line loss` | NULL | ⚠️ default 0% | optimistic (lossless) |
| `pto_date` | 2026-05-11 | ✅ plausible | past; curve effective from PTO |
| DC/AC ratio | 1.40 | ✅ plausible | 646 kW DC / 462 kW AC |

### 4.4 Impact and required remedy

Baseline #3 produces a **systematically wrong** Site 4 expected curve (negative or AC-saturated depending on temperature), plus a mild optimistic bias from the warnings. The **only constraint-compliant fix** is a corrected **replacement** baseline (Section 6): create a new draft with `thermal_coefficient_pct ≈ −0.35` (and ideally supplied losses/soiling), approve, and activate it — which supersedes #3. **Do not edit #3.** Because activation of a replacement is forward-only (Section 6.3), the period #3 was active is preserved as-is; a retroactive correction is an explicit, separate, audited operation (Section 8, Phase 5) and is out of this audit's scope.

---

## 5. Deliverable 4 — Approval / activation gate design

There are three natural enforcement points, today all unguarded for plausibility. The principle: **drafts are permissive (warn), activation is fail-closed (block)** — so exploration is cheap but nothing physics-breaking can ever go live.

### 5.1 Pre-draft gate (`create-draft-from-facts`, `routers/telemetry/v2.py:2817-2908`)

- **Today:** only required-present + numeric (`…:2854-2881`).
- **Proposed:** after readiness passes, run the Section 2 matrix over the merged values and return per-field `severity` (`plausible/warning/hard_invalid`) plus the compute-smoke-test result, carried in the existing `warnings` / `field_blockers` response fields (additive — no schema break).
- **Policy:** still **create** the draft even with hard-invalid values (drafts are working state), but tag `model_parameters_json.validation = {...}` and set a `has_hard_invalid` marker so downstream gates and the UI see it. (Alternative stricter policy — block draft creation on hard-invalid — is viable but reduces the draft's usefulness as a scratchpad; recommendation is warn-at-draft, block-at-activation.)

### 5.2 Pre-approval gate (`approve`, `routers/telemetry/v2.py:3094-3124`, `crud:270-291`)

- **Today:** only a status-transition check (`crud:274-281`).
- **Proposed:** before stamping `approved`, run the matrix. **Block (`409`)** if any required physics field is `hard_invalid`, *unless* an explicit `override_rationale` is supplied and recorded (mirrors the existing override-rationale guardrail elsewhere in DD). **Warnings** require an explicit acknowledgement that is persisted (e.g. in `notes` / `model_parameters_json`). This ensures a human consciously signs off on optimistic defaults or out-of-band values.

### 5.3 Pre-activation gate (`activate`, `routers/telemetry/v2.py:3127-3159`, `crud:293-332`) — **the safety net**

- **Today:** only the approval-status check + atomic supersede (`crud:301-332`).
- **Proposed:** **hard fail-closed.** Before flipping to `active`, run the matrix **and** the compute smoke-test. If **any** required physics field is `hard_invalid`, or the smoke-test yields negative/non-finite expected or an impossible derate factor at the probe temperatures (ordinary AC clipping is **not** a failure — §2.3.3), raise `BaselineActivationError` → `409` (reusing the existing error path, `routers/telemetry/v2.py:3148-3151`). **No override at activation** — a baseline that fails physics validation can never become the live curve. This is the gate that would have stopped baseline #3, and it is the **highest-value, lowest-risk** change because it:
  - touches no existing active row (it only guards new transitions),
  - cannot alter expected math (validation is a separate read-only function),
  - is a pure pre-condition added before the existing atomic supersede.

### 5.4 Shared rules across all three gates

- Validation lives in **one** function consumed by all three call sites (no divergence), exactly as the override-rationale guardrail is shared between `set_key` and `bulk_accept`.
- Validation is **read-only**: it computes verdicts, writes nothing, mutates nothing.
- Structured `409` bodies must be returned via `JSONResponse` (not raw `HTTPException` detail) when machine-readable fields are needed — consistent with the create endpoint's deliberate avoidance of the string-flattening global handler (`routers/telemetry/v2.py:2856-2859`).
- Never auto-correct, never auto-activate, never silently clamp.

---

## 6. Deliverable 5 — Replacement-baseline lifecycle

### 6.1 The invariant

A correction to an active baseline is **always a new baseline**, never an in-place edit. This is already structurally true: drafts get `version = max(version)+1` (`baseline_from_facts_service.py:1007`, `crud:222, 238-239`), idempotency is **draft-scoped only** so an active/approved baseline can never be short-circuited or overwritten (the bridge tests assert this), and `create_draft` always inserts a fresh `draft` row (`crud:213-268`).

### 6.2 The correction flow (for Site 4 and in general)

1. **Create** a corrected draft via `create-draft-from-facts` with the fixed reviewer constants (e.g. `thermal_coefficient_pct = -0.35`, `power_tolerance_min_pct ≤ 0`, supplied losses/soiling). Same equipment facts flow through unchanged. → new `draft`, new version.
2. **Approve** it (`/approve`) — now gated by §5.2.
3. **Activate** it (`/activate`) — now gated by §5.3.

### 6.3 What activation does (and deliberately does not do)

`crud.activate` (`crud:293-332`):

- enforces the approval gate (`:301-305`),
- locks the prior active row `FOR UPDATE`, sets it `superseded` with `active_to = now`, and links `supersedes_baseline_id` (`:307-321`),
- sets the new row `active`, `active_to = NULL`,
- sets `active_from = now` for a **replacement** (`has_prior` is true), and only backdates to PTO for the **first** active baseline (`:324-328`, `_first_active_from :33-52`).

**Consequence:** a replacement is **forward-only** — it drives buckets from `now` onward and **never rewrites the historical period** the superseded baseline owned. Period-effective selection then walks the supersede chain by `active_from` (`crud:162-208`), so historical reads still reflect the (corrupt) #3 for its active window, and the corrected baseline for everything after activation. This is intentional and constraint-aligned ("corrections create a NEW replacement baseline"; "never rewrite historical periods").

### 6.4 The retroactive-correction caveat

For Site 4 this means a replacement activated on 2026-06-20 leaves **2026-05-11 → 2026-06-20 still driven by the corrupt #3**. Truly re-stating that historical window is a **separate, explicit, audited** operation (it would have to set the replacement's `active_from` back to the corrupted window's start, overlapping/closing #3 deliberately). It is **not** done automatically and is **out of scope** here (see Section 8, Phase 5). The audit's recommendation is: fix forward now; decide on retroactive re-statement as a deliberate, signed-off action.

---

## 7. Deliverable 6 — O&M behavior when the active baseline is invalid

### 7.1 The gap today

The expected read path has honest states for *absence* but **not for invalidity**:

- No active baseline → overall `baseline_not_available`, no buckets (`expected_service.py:101-103, 28-29`).
- Per-bucket `pre_pto` / `missing_inputs` → expected NULL, never zero (`expected_service.py:343-387`).
- But a **present-but-invalid** active baseline (like #3) is computed with whatever is stored. `from_baseline` only guards against *missing* required fields, not implausible ones (`expected_service.py:153-162`), and `_expected_power_kw` has **no lower clamp** (`:333-334`). So the O&M / expected-preview surfaces (`routers/telemetry/v2.py:3162-3181`) render a corrupt — even **negative** — expected line with no warning.

### 7.2 Proposed read-time behavior (read-only, never mutating)

1. **Add an additive overall state `baseline_invalid`** to `ExpectedState` / the overall-status reporting (sits *alongside* the existing `expected_baseline_available` boolean — `expected_service.py:106-118` already establishes the additive-metadata pattern). It is computed by running the Section 2 validation (incl. the compute smoke-test) over the active baseline **at read time**.
2. **When the active baseline is `baseline_invalid`:** do **not** emit a fabricated/corrupt expected series. Return expected as **unavailable** with the distinct `baseline_invalid` reason (clearly different from `baseline_not_available`), so the loss/comparison math falls back to honest **N/A**, never 0 and never a negative number. This preserves the platform's "never fabricate zero" contract.
3. **Surface a banner** in the project Telemetry / O&M tab: e.g. *"Active baseline #3 has an invalid temperature coefficient (350 %/°C). Expected production is suppressed until a corrected replacement baseline is activated."* with a CTA to the create-replacement flow (Section 6).
4. **Prefer surfacing the reason over silent clamping.** A defensive lower-clamp (drop buckets where expected < 0) could be added as belt-and-suspenders, but clamping *alone* would hide the defect — the reason/banner is the primary mechanism; any clamp is secondary and must not replace the honest state.
5. **Never auto-deactivate** the bad baseline. The hard constraint forbids mutating #3; the read path only *refuses to display* a corrupt curve and *prompts* a human to create a replacement. Deactivation only ever happens via the normal supersede-on-activate of a corrected replacement (Section 6).

### 7.3 Why read-time (not just write-time) validation is needed

The activation gate (§5.3) prevents *future* bad baselines, but baseline #3 is **already active**. Only a read-time check can protect the live O&M view for an already-active invalid baseline without mutating it. The two gates are complementary: write-time prevents new corruption; read-time contains existing corruption honestly.

---

## 8. Deliverable 7 — Test plan + phased roadmap

### 8.1 Test plan

**Validation matrix (unit, pure function):**
- Each field at its plausible / warning / hard-invalid boundaries (table-driven).
- Thermal coefficient: `-0.35` plausible; `0.35` and `350` hard-invalid (sign + magnitude); `-0.0035` warning (per-unit).
- `power_tolerance_min_pct`: `0` / `-3` plausible; `5` warning; `50` hard-invalid.
- Loss-sum ≥ 100 hard-invalid; soiling > 1.05 hard-invalid; DC/AC ratio bands.
- **Compute smoke-test:** baseline #3's exact stored values → negative expected at 5 °C probe ⇒ hard-invalid; a corrected (`-0.35`) variant ⇒ pass.

**Lifecycle gates:**
- Draft with a hard-invalid value → created **with** `has_hard_invalid` + warnings (per chosen warn-at-draft policy), no auto-activation.
- Approve with hard-invalid → `409` unless `override_rationale` present; warnings require recorded acknowledgement.
- **Activate regression:** a baseline carrying `thermal_coefficient_pct = 350` → activation `409`, prior active untouched (this is the baseline-#3 regression test).
- Activate a valid corrected baseline → succeeds, supersedes prior (`active_to`, `supersedes_baseline_id` set), `active_from = now`.

**Read path:**
- Active baseline with hard-invalid physics → expected read returns `baseline_invalid`, NULL expected, **no negative numbers** surfaced, loss = N/A.
- Valid active baseline → unchanged output (golden test: byte-identical to today for known-good inputs — proves the formula was not altered).

**Guardrails / non-regression:**
- `from_baseline` still raises only on missing required (unchanged).
- `REQUIRED_PHYSICS_FIELDS` set unchanged (existing test already asserts this).
- No BigQuery / Firestore / SAFL / legacy reintroduced (existing `inspect.getsource` guard pattern).
- Validation function performs zero writes/commits (assert via a session spy / no row delta).

### 8.2 Phased roadmap (each phase shippable, additive, reversible)

| Phase | Scope | Risk | Touches active rows? |
|-------|-------|------|----------------------|
| **0 (this audit)** | Design only | none | no |
| **1** | Validation matrix module + bounds constants + compute smoke-test + full unit tests. No enforcement wiring. Surface as **non-blocking warnings** in the create-draft response. | low | no |
| **2** | Wire **pre-activation hard block** (§5.3) + the baseline-#3 activation regression test. Highest value, lowest risk. | low | no (guards transitions only) |
| **3** | Pre-approval gate + reviewer acknowledgement of warnings (§5.2); UI inline validation + thermal-coefficient helper/derived preview (§3.4). | medium | no |
| **4** | Read-path `baseline_invalid` state + O&M banner + replacement CTA (§7), read-only. | medium | no (read-only) |
| **5 (optional, explicit)** | Operator-driven **retroactive** correction tooling for an already-active invalid baseline (re-stating historical effective periods). Requires deliberate sign-off — touches historical windows. | high | yes — by deliberate, audited action only |

### 8.3 Recommended immediate operational action for Site 4 (not code)

Independently of the phases, Site 4's live curve is wrong now. The recommended one-time, manual, audited remediation is to **create a corrected replacement baseline** (`thermal_coefficient_pct = -0.35`, fix `power_tolerance_min_pct`, supply losses/soiling), approve, and activate it — superseding #3 per Section 6. **Do not edit baseline #3.** This is operational and is *not* performed by this audit.

---

## 9. Citation index

- Physics formula & constants: `app/services/telemetry/expected_service.py:78-92, 121-185, 296-405`
- Lifecycle CRUD (create/approve/activate/supersede, first-active backdate, period-effective): `app/crud/telemetry_expected.py:33-52, 120-208, 213-332`
- Facts→draft bridge (coerce/never-guess, unit warnings, readiness, create): `app/services/telemetry/baseline_from_facts_service.py:301-368, 941-1063`
- Lifecycle endpoints (create-draft / approve / activate / preview): `app/routers/telemetry/v2.py:2817-2908, 3094-3159, 3162-3181`
- Datasheet field conventions (thermal coeff example −0.35, min tolerance `le=0`, degradation examples): `app/schema/device_technical_detail/module.py:30-43`
- Create request schema (reviewer constants): `app/schema/telemetry_v2.py:895-910`
- Site 4 baseline id 3 stored row + provenance: live read-only DB inspection (Section 4).
