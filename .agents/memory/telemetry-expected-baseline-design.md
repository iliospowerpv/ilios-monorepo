---
name: Telemetry "expected" — two distinct notions + baseline preservation
description: The two different "expected" definitions in the telemetry stack, where each lives, and the rules for building a V2 PostgreSQL baseline.
---

# Two notions of "expected" (do not conflate)

**Why:** The live Actual-vs-Expected / Losses / Performance-Index charts were driven
by the *weather-adjusted physics* expected, NOT the PVsyst design estimate. Treating
"PVsyst baseline" as the chart source leads to the wrong V2 rebuild.

- **(A) PVsyst design estimate** — static contract forecast (annual P50/P90 MWh,
  specific yield, monthly Jan–Dec production, GHI). Extracted by DocAI
  (`docai/ilios-DocAI` PVSystPipeline, `terms/pv-syst/`). Reaches Postgres only as
  scalar summary values via `app/static/due_diligence_to_assets_keys_mapper.py`
  (consumed in `assets_management_helper.py`). **No 8760 hourly parser exists.**
- **(B) Weather-adjusted physics expected** — computed per 15-min interval in
  BigQuery SQL from measured irradiance + cell temp. Authoritative formula:
  `backend/rea-telemetry/.../templates/platform/site_power_actual_vs_expected.sql.jinja2`
  (+ `_daily`, `_and_irradiance`, `device_power_actual_vs_expected`).
  `expected_power = min(dc_nameplate_kw × system_derate × irradiance_factor ×
  temp_factor, ac_nameplate)`; derate = power_tolerance × soiling × age_factor ×
  dc_voltage_drop × inverter_efficiency × ac_voltage_drop; age anchored on PTO
  (NULL before PTO ⇒ expected NULL). Inputs from BQ `site_characteristics` /
  `device_characteristics`; config from Firestore `telemetry_config_{env}`.

# Key reproducibility fact
**How to apply:** V2 already ingests the (B) inputs — normalized metrics
`site_power_ac_kw`, `irradiance_wm2`, and cell temperature
(`app/helpers/telemetry/v2_chart_data.py`). So (B) is reproducible natively in
PostgreSQL/Python with NO BigQuery. (A) stays monthly/annual only until an 8760
parser is built — never synthesize hourly from monthly (that is fabrication).

# Native baseline foundation (compute-on-read)
- The native baseline lives in two PG tables (`telemetry_expected_baselines`
  typed-physics header + `_baseline_points`) plus a pure+DB calc service that ports
  the (B) jinja physics EXACTLY (verified line-by-line), with admin/preview endpoints.
  Weather-adjusted expected is **computed on read** from V2 rollups, NOT materialized
  into an interval-rollups table. **Why:** the inputs are already ingested, so
  materializing adds cache-invalidation burden with no extra consumer.
- Never-fabricate state machine is the contract: no active baseline ⇒
  `baseline_not_available`; bucket missing irradiance/cell-temp ⇒ `missing_inputs`;
  PTO null/before bucket ⇒ `pre_pto`; all of these mean expected = NULL, never 0.
  Only an active `weather_adjusted_model` baseline drives live expected (design
  estimate is NOT live).
- **`expected_baseline_available` boolean semantics diverge by level — gate on
  `expected_state`, not the bool.** Site-level sets the flag True whenever an active
  baseline exists, even when state is `missing_inputs`/`pre_pto` and every expected
  value is None; company-level sets it True only when state == `available`. So a True
  site flag does NOT guarantee any non-null expected — the FE must branch on
  `expected_state`. Per-site states: {available, partial, missing_inputs, pre_pto,
  baseline_not_available}; company states: {available, partial, baseline_not_available}
  + counts (sites_with_telemetry, sites_with_active_baseline, sites_missing_baseline).
- Company expected is honest-or-null: a real sum ONLY when EVERY telemetry-backed site
  is `available`; otherwise expected/loss = None (never 0). Do not infer device expected
  from site; inverter tiles stay neutral/N/A (no device-level expected).
- One-active per (site, baseline_type) enforced by a partial unique index
  `WHERE status='active'` PLUS a FOR UPDATE supersede in the activate tx. **Edge:** a
  true concurrent activation race surfaces as an IntegrityError 500 (not a clean 409)
  — accepted for the foundation, not a bug to chase.
- Percent columns are stored AS percent and divided by /100 exactly once in the calc;
  loss% is abs()-normalized and snapshotted (with PTO + site tz) onto the immutable
  baseline at creation; age is anchored on PTO via the baseline's snapshot tz.

# Baseline-build rules
- Postgres V2 = source of truth for actuals; BQ is not an app dep; do not route V2
  expected/loss through BQ; do not derive expected from actual.
- Human sign-off mandatory: reuse the DD chain (document_keys → project_facts
  candidate → human promote → active; audited in `assumptions_promotions`). Never
  auto-promote AI extraction to an active baseline.
- Proposed model: `telemetry_expected_baselines` (versioned header, status
  draft/in_review/approved/active/superseded, methodology pvsyst_design |
  weather_adjusted_physics, parameters JSONB, pvsyst_summary JSONB, provenance,
  effective dates, single-active partial unique index) + `telemetry_expected_baseline_points`
  (granularity hourly/daily/monthly/annual, metric, value).
- Loss columns (`site_additional_fields.{dc,ac,medium_voltage,mv_line}_loss`) appear
  as negative percentages in `site_details` examples but the BQ formula expects
  positive `%` subtracted `/100` — normalize sign+magnitude on import or expected is
  silently wrong.
- Charts + company/investor/portfolio aggregation now consume the native baseline for
  V2 sites (only the `site_has_v2_rollups` branches were rewired). The legacy layer is
  retained as the non-V2 fallback — do NOT remove it: BQ read layer + the `/api/om/...`
  chart fallbacks, rea-telemetry jinja templates (still the formula-of-record to diff
  against), Firestore config models, DocAI PVsyst pipeline + mapper + extraction
  registry, and parameter source columns all still back non-V2 sites.
- Shared validators (`calculate_actual_vs_expected`, performance-index, round) are
  None-safe and used by BOTH V2 and legacy paths, so legacy now also emits None
  (instead of 0/None÷100) for missing/undefined expected — an intentional honesty
  improvement; every consuming schema field is already Optional so no 500 risk.
