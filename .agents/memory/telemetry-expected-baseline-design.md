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

# Baseline-build rules (Phase 3 design)
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
- Do NOT remove until V2 baseline exists: BQ read layer + the 4 `/api/om/.../-chart`
  fallbacks, rea-telemetry jinja templates, Firestore config models, DocAI PVsyst
  pipeline + mapper + extraction registry, parameter source columns, and the
  `expected_baseline_available` flag contract.
