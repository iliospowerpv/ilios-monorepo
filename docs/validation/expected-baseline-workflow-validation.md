# Validation Report — End-to-End Weather-Adjusted Expected Baseline Workflow

**Mode:** Validation-only (no code/migration/schema/UI changes were made; none were required).
**Date:** 2026-06-19
**Validation subject site:** Site **4** — "110 Shawmut" (`company_id=6`, timezone `America/New_York`, not archived). **PROTECTED** (its telemetry mappings/facts must not be mutated).
**Baseline role/type validated:** `weather_adjusted_model` (the default produced by the facts→draft bridge).

## How this validation was performed (and its honest limit)

The workflow could **not** be driven through the authenticated UI end-to-end, because no `telemetry_admin` session on `company_id=6` was available in this environment. Validation was therefore performed by (a) reading the **live database ground truth** and (b) **exhaustive code-path verification** of every stage's service/CRUD/router. Where a claim depends on a runtime that was not exercised, it is labelled accordingly.

**Consequence to keep in mind:** there are currently **zero `telemetry_expected_baselines` rows on any site** (and zero `telemetry_expected_baseline_points`). The workflow has therefore **not yet been exercised on real data**. Site 4 is correctly staged at **"facts promoted, no baseline yet."** This is the expected pre-workflow state, **not a defect**.

## Database ground truth (at validation time)

| Fact | Value |
| --- | --- |
| `telemetry_expected_baselines` (all sites) | **empty** → no draft / approved / active / superseded anywhere |
| `telemetry_expected_baseline_points` (all sites) | **0** (no design-estimate points) |
| Site 4 `project_facts` | 42 **active** (promoted + accepted) + 42 **candidate** (accepted, not promoted) |
| Site 4 baseline-driving facts present | `module_wattage = "340 Wp"`, `inverter_wattage = "66 kWac"` — both **promoted active** |
| Site 4 physics-constant facts | **none** (no `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct`) |
| Site 4 `pto_date` fact | **none** |
| Site 4 V2 actuals | 109,829 readings, 8 devices; metrics `device_power_ac_kw`, `site_power_ac_kw`, `cell_temperature_f`, `irradiance_wm2`; 1h site rollups through 2026-06-19 |
| Native weather domain (`weather_sources`/`weather_observations`) | **empty** → weather physics inputs come only from DAS telemetry rollups via WeatherResolver (W1) |

## Step-by-step validation

### 1. Data Room → `project_facts` (acceptance / promotion) — **PASS**
`promotion_service.promote_version` runs the fail-closed **freshness guard** *before* any write and *before* the write transaction's try/except: it is a pure read (no commits/writes), is **all-or-nothing** (one stale candidate blocks the whole promotion → `PROMOTION_SOURCE_STALE` / HTTP 409), and **baseline-driving fields require provable parse lineage** even when the value matches (`no_lineage_baseline_field`). Promotion then atomically retires the prior active fact, promotes the candidate to active, writes an audit record, and commits; any exception rolls back. Due-diligence acceptance/override writes **only** to `project_facts` (no DD→BigQuery characteristics write). Evidence: Site 4 holds 42 active promoted facts including module/inverter wattage.

### 2. Reconciliation (read-only audit ladder) — **PASS**
`reconciliation_service.build_site_reconciliation` performs **zero** `session.add`/`commit`/`flush`/`delete` (the only `.add()` calls are on in-memory Python sets). It reads baselines/points **verbatim** (never recomputes), never promotes, and treats SAFL as display/comparison-only — **never** as a baseline source.

### 3. Readiness + unit normalization — **PASS (honest staging)**
`evaluate_readiness` reports the **full** required physics set: module/inverter fields are sourced from facts, while the reviewer-only datasheet constants are always reported `missing` here because they are supplied on the create request. For Site 4 the two wattage facts are **unit-bearing text** (`"340 Wp"`, `"66 kWac"`); the strict numeric coercion deliberately refuses to parse them (never guesses units). `baseline_input_normalization.propose` would offer `"340 Wp" → 340 W` and `"66 kWac" → 66 kW` (both `unit_strip`, `requires_confirmation=True`), **proposing only** — it never mutates the `project_facts` row and never applies a value without explicit reviewer confirmation. Net: **Site 4 readiness from facts alone is NOT ready** (it still needs the 5 reviewer datasheet constants, a PTO date, and the two wattage normalization confirmations). This is correct, honest staging — not a bug.

### 4. Draft creation (`create-draft-from-facts`) — **PASS**
The reviewer-confirmation validator (`_apply_normalization_confirmation`) is **anchored**: it requires both `source_fact_id` and `raw_value`, both must match the *current* active fact (stale/drifted/missing anchors are rejected with a re-confirm message), it recomputes the server's **own** normalized value (never trusts the front-end number), a unit *conversion* additionally requires an explicit `allow_conversion` flag, and a final tolerant cross-check (`values_match`) must agree. `create_draft_from_facts`: not-ready → **no row created** (router returns 422 with the readiness body); ready → idempotent on the source-fact signature, else a new draft at `version = max+1`; the row is always `status=draft`; and `site_additional=None` ("NEVER read SiteAdditionalFieldList for this bridge"). Activation is never a side effect of draft creation.

### 5. Review (`DraftBaselineReviewPanel`) — **PASS (code present; not re-exercised)**
The merged Approve/Activate UX panel surfaces draft provenance (source facts, reviewer inputs, normalized values, optional defaults, PTO, persisted warnings) and is permission-gated. Approve and Activate are separate explicit actions with distinct confirmation dialogs.

### 6. Approve (`POST /v2/expected-baselines/{id}/approve`) — **PASS**
Gated by `telemetry_admin_required` **plus** company-admin site authorization (`get_authorized_site_with_company_admin`) **plus** `_enforce_company_visibility`. Returns **404** if the baseline is missing. `crud.approve` only moves `draft`/`in_review`/`rejected → approved` (any other status raises → HTTP **409**), stamps reviewer + approver, and **does not activate** (activation is a separate step).

### 7. Activate (`POST /v2/expected-baselines/{id}/activate`) — **PASS**
Same gating (telemetry-admin + company-admin + company-visibility), 404 when missing. `crud.activate` only moves `approved → active` (else HTTP **409**); it locks the prior active row (`SELECT … FOR UPDATE`) and atomically **supersedes** it (`prior.status=superseded`, `prior.active_to=now`). The supersession pointer `supersedes_baseline_id = prior.id` is written on the **newly activating** baseline (not the prior row), which is then stamped `status=active`, `active_from=now`, `active_to=None`.

### 8. O&M expected surfaces — **PASS**
- **Today tile** (`apply_v2_actual_production`, single active baseline via `compute_site_expected`): no baseline → `expected_kw=None`, `cumulative_expected_kw=None`, `expected_state=baseline_not_available`, `baseline_id=None`. Never fabricated.
- **Comparative power** (`build_actual_vs_expected_section`) and **daily ratio** (`build_past_performance_section`) use `compute_site_expected_period_effective`. No covering baseline → `expected=None`/`baseline_id=None` (actual still rendered); `missing_inputs`/`pre_pto` buckets → `expected=None`; a daily bucket with no `ok` data → percent **`None`**, never `0%`.
- `derive_expected_state` summarizes to honest `baseline_not_available` / `missing_inputs` / `pre_pto` / `partial` / `available`.
For Site 4 **now** (no baseline) every expected surface correctly reports `baseline_not_available` / honest `None`, never a fabricated zero.

### 9. Historical integrity (period-effective) — **PASS**
`compute_site_expected_period_effective` stitches one sub-window per overlapping baseline; `_effective_baseline_at` resolves ownership over `[active_from, active_to)` with latest-`active_from` winning, so a supersede-boundary bucket belongs to the **new** baseline (counted once). Buckets in periods **before** the earliest `active_from` have no covering baseline and are simply **absent** (rendered as honest gaps, never fabricated). `get_baselines_effective_in_window` admits only `active`/`superseded` rows of the type. Therefore **activating a new baseline never rewrites prior periods**.

### 10. Regression / guardrails — **PASS**
- **No SAFL-as-baseline:** the facts→draft bridge passes `site_additional=None`; SAFL appears only as display/comparison in reconciliation. (The deprecated SAFL-snapshot create-baseline endpoint still exists for manual/backfill use but is **not** part of this workflow.)
- **No BigQuery/Firestore** in the supported facts→draft + V2 expected/chart workflow files (`expected_service` and the bridge state this explicitly; grep confirms none). Scope note: O&M chart routes retain a **legacy BigQuery fallback** for sites with **no** V2 rollups (V2-first precedence); Site 4 **has** V2 rollups, so it stays on the V2 path and never touches that fallback.
- **No fabrication / zero-fill / backfill** anywhere on the expected path; honest `None`/`N/A` throughout.
- **No design-estimate point creation** in this path (points table remains empty).
- **Untouched by design:** expected-math, ingestion, WeatherResolver, eligibility classifier, scheduler — none modified.
- The only state mutated by the workflow is `project_facts` (+ `accepted`/promotion audit), exclusively via the intentional promotion UI action.

## Issues found

**None at any severity.** All ten stages either PASS or are in correct honest-staging.

| Observation | Severity | Notes |
| --- | --- | --- |
| Workflow not yet exercised on real data (zero baseline rows) | INFO | Expected pre-workflow state; Site 4 correctly staged at "facts promoted, no baseline yet." |
| Site 4 readiness-from-facts is NOT ready | INFO | By design: 5 reviewer datasheet constants + PTO + 2 wattage normalization confirmations are supplied at create-draft time, not stored as facts. |
| Site 4 has no `pto_date` fact | INFO | Until a PTO is supplied at draft creation, expected buckets are `pre_pto` (suppressed) — honest, by design. |
| Deprecated SAFL-snapshot create-baseline endpoint still returns 201 (logs a warning) | INFO | Not used by this workflow; retained for manual/backfill only. No action. |

## Recommended follow-ups (operational, not code changes)

1. To exercise the full workflow on Site 4, a `telemetry_admin` on `company_id=6` should: confirm the module/inverter wattage normalizations, supply the 5 datasheet constants and a PTO date at create-draft time, then **review → approve → activate**. After activation, re-verify the O&M comparative/historical charts render a real expected line for post-PTO windows and honest gaps before PTO.
2. No code remediation is recommended — all guardrails hold as specified.
