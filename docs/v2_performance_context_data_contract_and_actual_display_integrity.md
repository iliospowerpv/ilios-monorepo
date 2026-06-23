# V2 Performance Context Data Contract & Existing Actual-Display Integrity

**Status:** Design & remediation-planning sprint — **no production code changes in this
sprint** unless a *separately approved*, narrowly-scoped, fully-validated null-display
correction is authorized (§5).
**Scope:** Read-only design. Defines the single V2-native read model for actual-vs-expected
performance context, the actual-state taxonomy, the correction plan for the missing-actual →
`0` honesty bug, weather presentation boundaries, Site 4 validation, migration/compatibility,
phased implementation, validation, and the do-not-touch list.
**Companion:** Builds on `docs/om_weather_and_performance_context_ui_audit.md` (accepted). That
audit identified the two parallel pipelines and the `?? 0` actual coercion; this document
defines the canonical contract and the remediation plan.
**Date:** 2026-06-23

---

## 0. Purpose, scope & non-negotiable governance

### 0.1 Objective
Define the **single V2-native read model** ("Performance Context contract") that will power, in
one consistent shape and on one aligned time axis:
- O&M actual-versus-expected performance charts;
- the new read-only **Performance Context** panel;
- Project Hub summary widgets;
- future investor reporting disclosures (context only).

This sprint also plans the **correction for missing actual values currently rendered as `0`**.

### 0.2 Hard constraints (binding on every decision below)
1. **No BigQuery, Firestore, SAFL, or legacy telemetry as operational truth.** The contract
   reads only PostgreSQL rollups + native baselines + native governance tables.
2. **No expected/baseline formula change.** Expected math stays exactly as in
   `expected_service.py`; the contract *composes* it, never recomputes it.
3. **No weather declaration change.** Semantics governance (WS.1–WS.4) is read verbatim.
4. **No WS.5 work.** Governed weather stays **context-only**; never an input to the active
   expected model in this contract.
5. **No fabricated nulls, zeroes, weather semantics, or causal explanations.** Honest states
   only.
6. **No automatic retirement of any existing endpoint** until every current consumer is
   inventoried and migrated safely (§5.4).
7. **The `0` vs `null` distinction is sacrosanct** (§2.2): `0` = measured/computed zero;
   `null` = unavailable / not applicable / unknown; negative nighttime tare/parasitic values
   are preserved, never coerced.

### 0.3 The integrity problem this sprint fixes
A missing **actual** value is today silently rendered as `0`, both on the backend (the O&M
chart helper, §1.A) and on the frontend (the Actual Production widget's `?? 0`, §1.A.9). A `0`
kW reading and "no telemetry for this interval" are **operationally opposite** — the first can
read as a real outage, the second is a data gap — yet both currently render identically. The
canonical contract and the widget correction (§5) make the two states distinct and honest.

---

## 1. Pipeline trace (the two actual-versus-expected pipelines)

The headline architectural fact: there are **two pipelines**, and **both are already
V2-first** for **actuals** — they read the **same V2 PostgreSQL rollup tables**
(`telemetry_site/device_interval_rollups`). **Only the O&M chart pipeline additionally
composes native baselines** (`telemetry_expected_baselines` + `expected_service`) to produce
**expected**; the V2-native `/series` pipeline reads **rollups only and carries no expected /
no baselines at all**. They differ in **response shape, bucketing/windowing, null discipline,
and whether they carry expected** — not in their underlying source of *actual* truth.

### 1.A Pipeline 1 — "O&M chart" pipeline

| Attribute | Detail (verified against source) |
| --- | --- |
| **Endpoints** | Site: `GET /api/operations-and-maintenance/sites/{id}/actual-production-chart`, `/actual-vs-expected-chart`, `/past-performance-chart`, `/inverters-performance-chart`. Company: `/companies/{id}/actual-production-chart`, `/actual-vs-expected-production-chart`, `/loses-for-a-day-chart`. (Router: `app/routers/operations_and_maintenance/sites.py`, `companies.py`.) |
| **Source tables / services** | `telemetry_site_interval_rollups` / `telemetry_device_interval_rollups` (via `TelemetrySiteRollupCRUD` / `TelemetryDeviceRollupCRUD`) for **actuals + irradiance**; `telemetry_expected_baselines` (via `TelemetryExpectedBaselineCRUD`) + `expected_service.py` for **expected**. All reshaping lives in `app/helpers/telemetry/v2_chart_data.py`. |
| **Actual calculation path** | `apply_v2_actual_production` (current/cumulative) and `build_actual_vs_expected_section` / `build_past_performance_section` (time series) read `site_power_ac_kw` 1h rollups. "Current" = latest 1h bucket today (else latest overall); "cumulative" = Σ today's 1h avg-power buckets (kWh ≈ avg-kW over 1h). |
| **Expected calculation path** | `compute_site_expected` (live now-field) / `compute_site_expected_period_effective` (history) from the **`weather_adjusted_model`** baseline; expected formula unchanged. Per-bucket `expected` is `None` for `missing_inputs`/`pre_pto`; the live `expected_kw` is **strictly bucket-aligned** to `actual_kw` (no cross-bucket borrowing). |
| **Baseline-selection behavior** | Live "now" fields use the **current active** baseline (`get_active`). Historical sections use **period-effective** selection: each bucket uses the baseline that was active during that bucket's period (`active_from`/`active_to`), so activating a new baseline never rewrites prior expected. Active baseline is **validated on read** (`validate_baseline(..., "read_time")`); a still-active-but-invalid baseline yields `baseline_invalid` (expected suppressed to `None`, actual still shown) without any mutation. |
| **Weather / irradiance fields** | The site `actual-vs-expected-chart` returns a per-period **`irradiance`** (W/m², `irradiance_wm2` rollup mean). The site `actual-production-chart` returns a coarse **`weather`** descriptor (`{weather_description, weather_icon_url}`). **No temperature. No governed semantics.** |
| **Timezone & bucket** | Bucket **fixed at `1h`** (`CHART_BUCKET_SIZE`). Windows fixed: now/today (live), **7 days** (`actual-vs-expected`, `past-performance`). "Today"/daily boundary uses the **site IANA timezone** (`_site_local_day_start_utc`, `_site_local_date`); fallback UTC + warning. Timestamps are **naive-UTC** over the wire. |
| **Null / zero / negative handling** | **Expected:** honest `None` (never 0) for no-baseline / invalid / missing-inputs / pre-PTO. **Actual & irradiance:** *coerced to `0.0`* in several places because the schema fields are **non-optional**: `apply_v2_actual_production` sets `actual_kw`/`cumulative_actual_kw` to `0.0` when no bucket (lines ~197–200); `build_actual_vs_expected_section` / `_actual_irradiance_series` fill `actual`/`irradiance` with `0.0` for any bucket missing that metric; the legacy BQ-failure branch sets all four to `0.0` (lines ~145–148). Daily past-performance percent is honest `None` for a day with no `ok` bucket. **This is the integrity gap.** |
| **Consumers** | O&M Site Overview widgets (`ActualProduction`, `ActualProjectedPower`, `PastPerformance`, inverter tiles); O&M Company Overview (`ActualProduction`, `ProductionProjected`, `Losses`); PH Company "Performance" tab; My Portfolio "Companies" widget. |
| **Legacy dependencies** | BigQuery (`TelemetrySiteBigQuery` / `TelemetryDeviceBigQuery`, `get_production_chart_data_per_site`) is **only** reachable when the site has **no** V2 rollups **and** `legacy_telemetry_enabled()` is true (**off by default**). With the flag off, non-V2 sites return honest empty + `expected_baseline_available=False`. |
| **Verdict** | **V2 operational truth** when the site has rollups (the default and only live path); BigQuery is gated-off compatibility only. The **response shape is the legacy O&M shape**, which is what forces the `0.0` actual fill. |

#### 1.A.1 Company-level O&M endpoints (expected behavior differs from site-level)
The company O&M endpoints share Pipeline 1's V2-first actual path but have **distinct expected
semantics** (verified in `companies.py` + `v2_company_data.py`) — they must NOT be described
with the site-level expected behavior:
- **`/companies/{id}/actual-production-chart`** — aggregates per-site V2 actuals
  (`aggregate_company_actuals`); sites **without** V2 rollups contribute `0` to the actual
  total, and `total_expected_kw` is `None` with `expected_baseline_available=False` (**no
  company-level expected baseline exists**).
- **`/companies/{id}/actual-vs-expected-production-chart`** — **V2 carries actuals only**;
  per-site expected is `null` and the section is flagged `expected_baseline_available=False`.
- **`/companies/{id}/loses-for-a-day-chart`** — strict aggregate: returns today's expected
  when computable, otherwise `null` with `expected_state` explaining why (never a fabricated
  aggregate expected).

Implication for the contract: a company/portfolio Performance Context rollup (later phase)
must treat expected as **per-site composed then aggregated over `ok` buckets only**, never a
company-level baseline, and must carry the same honest-null discipline (the company actual
aggregation's "missing site → 0 contribution" is itself a candidate for the §5 integrity
review).

### 1.B Pipeline 2 — "V2-native series" pipeline

| Attribute | Detail (verified against source) |
| --- | --- |
| **Endpoints** | `GET /api/telemetry/v2/sites/{id}/series` (one metric), `/device-series` (per device), `/latest` (newest value + freshness per metric). (Router: `app/routers/telemetry/v2.py`.) |
| **Source tables / services** | `telemetry_site_interval_rollups` / `telemetry_device_interval_rollups` directly via `TelemetrySiteRollupCRUD.get_series` / `TelemetryDeviceRollupCRUD.get_series`; latest via `get_latest_per_metric` + `TelemetryReadingCRUD.latest_metric_ts`. |
| **Actual calculation path** | Returns rollup rows verbatim as `{bucket_start, value, sample_count, completeness}` for the requested **normalized metric** (`site_power_ac_kw`, `device_power_ac_kw`, `irradiance_wm2`, `cell_temperature_f`, …). `value` is the interval **mean**. |
| **Expected calculation path** | **None.** This pipeline carries no expected/projected series at all. |
| **Baseline-selection behavior** | N/A (no expected). |
| **Weather / irradiance fields** | Same endpoints with `metric=irradiance_wm2` or `metric=cell_temperature_f` return the **granular** rolled-up means. The **metric name does not assert semantics** — semantics come only from the governance layer (§6). |
| **Timezone & bucket** | Bucket **selectable** (`15m`/`30m`/`1h`/`1d`, validated). Window **selectable** (`from`/`to`, clamped by `_clamp_series_window`). Timestamps **naive-UTC**. No site-tz day boundary (caller controls window). |
| **Null / zero / negative handling** | **Honest.** Empty `points` list (HTTP 200) when no rollups; **never zero-fills** missing buckets; genuine zero and negative tare preserved (`value=float(row.value)`). `completeness` is `None` when unknown. **This is the honesty model to standardize on.** |
| **Consumers** | PH `DevicePerformanceCard` (`device-series`, `device_power_ac_kw`, 1h, 24h); Telemetry tab freshness (`/latest` via `useSiteLatestTelemetry`); various readiness/health reads. |
| **Legacy dependencies** | **None.** Pure PostgreSQL. |
| **Verdict** | **V2 operational truth.** Honest nulls, granular weather, selectable bucket/window — but **no expected and no governance composition**. |

### 1.C Comparison & conclusion

| Dimension | Pipeline 1 (O&M chart) | Pipeline 2 (V2 series) |
| --- | --- | --- |
| Actual source | `site_power_ac_kw` rollups | rollups (any metric) |
| Expected | Yes (active / period-effective baseline) | **No** |
| Granular weather | irradiance only (coarse `weather` text) | irradiance **and** temperature (granular) |
| Governed semantics | No | No (but metric is granular) |
| Bucket / window | fixed 1h / fixed today·7d | selectable |
| Missing actual | **rendered as `0`** (non-optional schema + FE `?? 0`) | **honest empty / gap** |
| Negative tare | preserved when present (but missing→0) | preserved |
| Legacy fallback | BigQuery (gated off) | none |

**Conclusion:** neither pipeline alone is the right home for Performance Context. Pipeline 1
has expected + history but the wrong (zero-coercing) null discipline and a legacy shape;
Pipeline 2 has the right null discipline + granular weather but no expected and no governance.
The recommended path (§2) is a **new read-only aggregator** that adopts Pipeline 2's honest
null discipline, composes `expected_service` (Pipeline 1's expected math, unchanged) and the
weather-semantics + eligibility governance, and exposes a single nullable-everywhere contract.

---

## 2. Canonical V2 Performance Context contract

### 2.1 Endpoint & envelope (proposed, Phase 1)
`GET /api/telemetry/v2/sites/{site_id}/performance-context?window=&bucket=&temp_unit=`
- **Read-only, composition-only.** Reads rollups + `expected_service` +
  `semantics_reconciliation_service` + `device_eligibility_diagnostics_service` +
  readiness/health. **No writes/commits; never calls activate/promote/revalidate/ingest.**
- Auth: asset-view + company-visibility (same as the existing V2 read endpoints).
- `bucket ∈ {15m,30m,1h,1d}`; `window` = a bounded range or preset (Today/24h/7d/30d/custom,
  clamped); `temp_unit ∈ {f,c}` (display conversion only, °F default).

```jsonc
{
  "site_id": 4,
  "site_timezone": "America/New_York",  // IANA tz; affects ONLY the 'today'/daily boundary
  "bucket_size": "1h",
  "window": { "start": "2026-06-22T00:00:00", "end": "2026-06-23T00:00:00", "tz_note": "all timestamps are naive-UTC; site_timezone affects only day/'today' boundaries" },
  "series": [
    {
      "bucket_start":            "2026-06-22T13:00:00",  // canonical key (naive-UTC), kept for back-compat
      "bucket_start_utc":        "2026-06-22T13:00:00",  // explicit naive-UTC
      "bucket_start_site_local": "2026-06-22T09:00:00",  // display convenience (site tz); never a query key
      "actual_kw":        123.4,        // nullable; null = no actual telemetry this bucket
      "actual_kwh":       123.4,        // nullable; derived from avg-kW × bucket-hours
      "actual_state":     "available",  // §3 taxonomy (per-bucket)
      "expected_kw":      130.0,        // nullable; null = honest expected gap, NEVER 0
      "expected_kwh":     130.0,        // nullable
      "expected_state":   "available",  // available|partial|missing_inputs|pre_pto|baseline_not_available|baseline_invalid
      "baseline_id":      57,           // nullable; the baseline that produced this bucket's expected
      "variance_kwh":     -6.6,         // nullable; present ONLY when actual & expected both valid
      "variance_pct":     -5.1,         // nullable; present ONLY when expected_kwh > 0
      "irradiance_wm2":   612.0,        // nullable; observed rolled-up mean
      "temperature":      31.2,         // nullable; observed rolled-up mean, in temp_unit
      "sample_count":     12,           // nullable; from rollup
      "completeness":     0.95,         // nullable; per-series cadence-inferred ratio
      "source_provenance": {            // per-bucket provenance, read verbatim from the underlying rows (never invented)
        "actual_metric": "site_power_ac_kw", "actual_unit": "kW", "actual_agg": "mean",
        "expected_baseline_id": 57, "baseline_selection_mode": "period_effective",
        "irradiance_metric": "irradiance_wm2", "irradiance_source_id": 12,
        "temperature_metric": "cell_temperature_f", "temperature_source_id": 12,
        "weather_declaration_mapping_id": 88   // nullable; the governed mapping (if any) backing the weather labels
      }
    }
  ],
  "weather_semantics": {                // site-level; a backend-composed PROJECTION of WeatherSemanticsReconciliationResponse — labels/states copied verbatim, never re-derived (see §2.4)
    "irradiance": { "label": "Observed irradiance — semantics unverified", "plane": "unknown", "basis": "legacy_das_unverified", "expected_model_eligible": false, "used_by_active_model": false },
    "temperature": { "label": "Observed temperature — semantics unverified", "type": "unknown", "basis": "legacy_das_unverified", "expected_model_eligible": false, "used_by_active_model": false },
    "headline_state": "observed_weather_device_no_governed_declaration",
    "blocking_level": "lowers_confidence"
  },
  "baseline_status": {                  // active baseline + provenance for deep-linking
    "expected_state": "available",
    "active_baseline_id": 57,
    "baseline_invalid": false,
    "invalid_baseline_id": null,
    "validation_summary": null,
    "required_action": null
  },
  "telemetry_quality": {               // from readiness/health + latest
    "latest_reading_at": "2026-06-22T13:55:00",
    "mapped_devices": 8,
    "eligible_devices": 8,
    "completeness_pct": 0.95,
    "freshness_state": "fresh"         // fresh|stale|no_data
  },
  "summary": {                         // over the selected window
    "actual_energy_kwh":   2950.0,     // nullable
    "expected_energy_kwh": 3100.0,     // nullable; over ok buckets only
    "variance_kwh":        -150.0,     // nullable
    "variance_pct":        -4.8,       // nullable
    "peak_irradiance_wm2": 940.0,      // nullable
    "expected_state":      "partial",  // window-level rollup of per-bucket expected_state
    "actual_state":        "partial"   // window-level rollup of per-bucket actual_state
  }
}
```

### 2.2 The `0` vs `null` contract (the core integrity rule)
- `0` = a **measured or computed zero** (e.g. real night-time zero production, a genuine zero
  expected). Always preserved.
- `null` = **unavailable / not applicable / unknown** (no telemetry, no baseline, pre-PTO,
  inputs absent). Rendered as `N/A`/`Unavailable`/the applicable state — **never** `0`.
- **Negative nighttime tare / parasitic load values are preserved**, never clamped to 0 or
  hidden. (This is why a blanket "negatives→0" or "round up" rule is forbidden.)
- **`expected` unavailable is an explicit expected-state, never fabricated.**
- **`actual` unavailable is an explicit actual-state, never zero-filled.**
- **Every metric in §2.1 supports true `null`.** This is the contract's defining property and
  the chief difference from the current O&M shape, whose `actual`/`irradiance` are non-optional.

### 2.3 Field-level semantics (selected)
- **`actual_kw` / `actual_kwh`** — rolled-up mean power and its kWh integral over the bucket;
  `null` when the rollup has no row for the bucket. `actual_kwh = actual_kw × bucket_hours`
  (kept consistent with the existing `BUCKET_SIZE_TO_HOURS` convention).
- **`expected_kw` / `expected_kwh`** — from `expected_service` (`weather_adjusted_model`
  baseline); `null` for `missing_inputs`/`pre_pto`/`baseline_invalid`/`baseline_not_available`.
  **Never 0.** Bucket-aligned to the actual (no cross-bucket borrowing).
- **`variance_*`** — computed only when **both** `actual` and `expected` are valid for the
  bucket and (for `variance_pct`) `expected_kwh > 0`. Otherwise `null` with the reason carried
  by `actual_state`/`expected_state`. Re-uses `calculate_actual_vs_expected` semantics; never
  invents a comparison when one side is missing.
- **`irradiance_wm2` / `temperature`** — observed rolled-up means; `null` for missing buckets.
  Their **display labels are governed by `weather_semantics`** (§6), never by the metric name.
- **`completeness`** — per-series cadence-inferred ratio (median sample gap → received/expected)
  as already computed in the rollup layer; `null` when not inferable.
- **`weather_semantics` / `baseline_status` / `telemetry_quality`** — read **verbatim** from
  the existing governance/diagnostics services; the contract never re-derives them (§2.4).
- **Timezone fields** — `bucket_start` / `bucket_start_utc` are **naive-UTC** (the storage and
  query key); `bucket_start_site_local` is a **display convenience** derived from
  `site_timezone` and is **never** a query key. `site_timezone` affects **only** the
  "today"/daily boundary, consistent with `_site_local_day_start_utc` / `_site_local_date`.
- **`source_provenance`** — per-bucket pointers (metric/unit/agg for actual, baseline id +
  selection mode for expected, metric + source/declaration-mapping ids for weather) **copied
  verbatim** from the rows that produced each value, so every displayed number is traceable to
  its origin. The aggregator **never fabricates** a provenance id; absent provenance is `null`.

### 2.4 The `weather_semantics` envelope is a verbatim projection (not a re-derivation)
The compact `weather_semantics` block in §2.1 is **not a new computation** — it is a
**backend-only projection** of the existing `WeatherSemanticsReconciliationResponse`
(`GET /api/weather/sites/{id}/semantics-reconciliation`, produced by
`semantics_reconciliation_service.py`). Rules:
- The headline state, per-metric `label`, `plane`/`type`, `basis`, `expected_model_eligible`,
  and `blocking_level` are **copied verbatim** from the reconciliation rows/site summary; the
  aggregator selects/maps fields but **never invents a label or recomputes a state**.
- `used_by_active_model` is **always `false`** in this contract (WS.5 deferred — §0.2).
- The frontend renders these strings **as-is**; it must **not** translate `unknown`/`basis`
  into a POA/cell claim or any other semantic upgrade.
- To avoid even the appearance of re-derivation, the build sprint may instead **embed the
  reconciliation rows verbatim** (full `WeatherSemanticsReconciliationRow[]`) and let the
  panel read them directly; the compact block then becomes a pure convenience summary. Either
  way, the **mapping lives in the backend aggregator, never in the FE**.

---

## 3. Actual-state taxonomy

A per-bucket (and window-rollup) **`actual_state`**, parallel to the existing
`expected_state`. **Missing actual telemetry must NOT be inferred as an outage.**

| `actual_state` | Meaning | How derived (read-only) |
| --- | --- | --- |
| `available` | Actual present for the bucket | rollup row exists with a value |
| `partial` | Some buckets present, some missing across the window | window-level rollup |
| `telemetry_unavailable` | No actual telemetry for the bucket/window | no rollup row + no recent reading |
| `telemetry_stale` | Mapped & previously reporting, but latest data is older than the freshness threshold | `latest_reading_at` / sync-job freshness vs threshold |
| `no_production_during_interval` | A **genuine measured zero** (e.g. night) | rollup row exists with value `0` (and within a plausible no-sun window) |
| `pre_pto` | Interval predates permission-to-operate | site PTO date vs bucket |
| `insufficient_data` | Row(s) present but completeness below a usable threshold | `completeness` below threshold |
| `not_applicable` | Metric/period not applicable for this site/device | structural (e.g. device category) |

**Rules:**
- `telemetry_unavailable`/`telemetry_stale`/`insufficient_data` are **data-quality** states →
  render `N/A`/`Unavailable`, never `0`.
- `no_production_during_interval` is the **only** state that renders a literal `0`, and only
  when the rollup genuinely measured `0`.
- The taxonomy **never asserts an outage or root cause** from absent telemetry (governance
  rule 5 + the variance policy in `om_weather_and_performance_context_ui_audit.md` §D).

### 3.1 Companion taxonomies (read verbatim, for the same panel)
- **`expected_state`** (existing, unchanged): `available` · `partial` · `missing_inputs` ·
  `pre_pto` · `baseline_not_available` · `baseline_invalid`. Always `null` expected, never 0.
- **Weather-semantic state** (existing 9-state reconciliation): see §6 / audit §C.3.
- **Baseline state** (existing): active / draft / invalid / unavailable + provenance ids.

---

## 4. (Reserved — see §6 for weather presentation; §5 for the widget correction)

---

## 5. Existing Actual Production widget correction plan

**This is the only place a production code change may occur in this sprint, and only if the
narrow null-display correction is separately approved.** It does **not** alter raw telemetry,
rollups, expected logic, or baseline logic.

### 5.1 The exact current behavior (to change)
`.../widgets/ActualProduction/ActualProduction.tsx`:
- `const { system_size_ac = 0, system_size_dc = 0, weather = 'Sunny' } = data || {};`
- `actual_kw = alignment === 'current' ? (data?.actual_kw ?? 0) : (data?.cumulative_actual_kw ?? 0);`
- `actual_vs_expected = … ?? 0;` and the gauge "rest" segment `100 - actualVsExpected ?? 0`.

A missing **actual** therefore renders as `0` kW / `0%` and a default "Sunny" chip. (Note:
**expected** is already honest here via `resolveExpectedState` → `N/A` + reason; only the
**actual** path is wrong.)

Backend counterparts that also coerce (deeper fix, see §5.3): `apply_v2_actual_production`'s
`else 0.0` for `actual_kw`/`cumulative_actual_kw`; the `0.0`-fill of non-optional
`actual`/`irradiance` in the section builders; the legacy BQ-failure `0.0` branch.

### 5.2 Required UI behavior change (narrow, frontend-only)
- Replace `data?.actual_kw ?? 0` / `cumulative_actual_kw ?? 0` with an **honest render**: when
  the value is `null`/`undefined`, show **`N/A` / `Unavailable`** (or the applicable
  `actual_state` once the contract ships), **not `0`**. (The backend already returns `null`
  actual on the no-V2 / legacy-off path, so this FE fix has immediate, safe value.)
- **Preserve genuine `0` and negative values** — only `null`/`undefined` map to N/A. Do not
  introduce a "negatives→0" or "round up" rule.
- Stop defaulting `weather` to `'Sunny'`; render the weather chip **only** when a descriptor is
  present, and label it as **observed/contextual** (never implying a governed/causal claim).
- The gauge/percent: when actual or expected is unavailable, show **"Variance N/A"** rather
  than a `0%` ring.
- Show a **data-quality explanation** and a **deep link** (Telemetry tab / Reconciliation)
  where appropriate (mirrors the existing `expected_state` caption pattern).

### 5.3 Deeper backend correction (contract-level, NOT in the narrow FE fix)
The section builders 0.0-fill `actual`/`irradiance` because
`SiteActualVSExpectedPerformanceListSchema` makes them **non-optional**. Truly honest actual
nulls in the *time-series* require **nullable** `actual`/`irradiance` — which is exactly the
new contract (§2). So:
- **Narrow/now (if approved):** FE-only render fix for the KPI widget (`actual_kw` /
  `cumulative_actual_kw` are already nullable on the no-data path).
- **Proper/Phase 1:** the new `performance-context` contract with nullable everything; migrate
  consumers to it; then the O&M section shape's 0.0-fill is no longer the source of truth.
- **`apply_v2_actual_production` `else 0.0`:** change to `else None` so a V2 site with no
  current bucket reports `null` (honest) instead of `0` — but this touches the O&M response and
  must be validated against every consumer first (§5.4); it is **not** part of the FE-only
  narrow fix.

### 5.4 Consumer inventory (must precede any endpoint retirement — constraint 6)
Before retiring/altering any O&M `…-chart` endpoint or changing its null contract, inventory &
migrate: `ActualProduction`, `ActualProjectedPower`, `PastPerformance`, inverter tiles, company
`ActualProduction`/`ProductionProjected`/`Losses`, PH Company "Performance", My Portfolio
"Companies". Endpoints stay **dual-served** (old shape + new contract) until all are migrated.

---

## 6. Weather presentation boundaries

Observed weather **values** may be displayed; **labels are governed** and read verbatim from
the semantics-reconciliation response (`GET /api/weather/sites/{id}/semantics-reconciliation`)
— never re-derived client-side.

| Condition (governed) | Irradiance label | Temperature label |
| --- | --- | --- |
| Active, physics-usable, plane = POA / type ∈ {cell,module,modeled_cell} | **POA irradiance** | **Cell/Module temperature** |
| Active, governed, other plane/type | **GHI irradiance (governed)** | **Ambient temperature (governed)** |
| Observed, no/!active declaration | **Observed irradiance — semantics unverified** | **Observed temperature — semantics unverified** |
| No source | **Irradiance source missing** | **Temperature source missing** |

- **"Weather data is contextual only"** until WS.5 integration exists. `expected_model_eligible`
  may be `true`, but `used_by_active_model` is **always `false`** in this contract (WS.5
  deferred) — at most show "Eligible — integration pending".
- **No causal language, no root-cause conclusion.** Correlation visuals are allowed
  (irradiance aligned under power on a separate axis); correlation **captions** are not (see
  audit §D tiers).

---

## 7. Site 4 (110 Shawmut) validation

Site 4 is the canonical case (and the protected telemetry-mapping site; this sprint touches
**no** mappings). The Performance Context for Site 4 must demonstrate:
- **V2 actual curve** — `site_power_ac_kw` rollups (real data), with honest **gaps** for
  missing buckets and **`actual_state`** per bucket (never `0`-filled).
- **Expected curve where valid** — modeled; otherwise the true `expected_state` chip.
- **Observed irradiance and temperature** — granular V2 rollups, labeled **"Observed … —
  semantics unverified."**
- **Current weather state (exact):** `observed_weather_device_no_governed_declaration`.
- **Expected-model eligibility** surfaced as **eligible/ineligible**, with
  `used_by_active_model = false` (WS.5 deferred).
- **Exact null behavior:** any missing bucket renders as a **gap / `N/A`**, with the precise
  `actual_state` (e.g. `telemetry_unavailable` vs `no_production_during_interval`) — confirming
  the integrity fix.
- **No UI calls it POA, and no UI says weather explains variance.** Narrative stays in the
  "no inference" / "possible contextual signal" tiers only.

---

## 8. Migration & compatibility strategy
1. **Additive-only first.** Ship the `performance-context` aggregator as a **new** endpoint;
   change **no** existing endpoint's behavior in Phase 1.
2. **Dual-serve.** O&M `…-chart` endpoints keep their current shape while consumers migrate to
   the contract. No endpoint is retired until §5.4's inventory is fully migrated.
3. **Honest-null rollout.** The contract is nullable-everywhere from day one. The narrow FE
   widget fix (§5.2) can land independently (it only changes rendering of already-nullable
   fields). The backend `else 0.0 → else None` change (§5.3) lands only with consumer
   validation.
4. **No data migration.** No backfill, no rollup/baseline rewrite, no schema change to
   telemetry tables. The new endpoint is pure read composition. (If the O&M section schema is
   later made nullable, that is an additive schema relaxation, validated per consumer.)
5. **Feature-flag the panel** so it can be enabled per environment without affecting existing
   charts.

---

## 9. API & frontend implementation phases
1. **Phase 1 — contract (backend, read-only):** `GET /…/performance-context` aggregator
   (§2), composition-only, fully unit/integration-tested against existing services. No UI.
2. **Phase 1b — narrow integrity fix (if separately approved):** FE-only Actual Production
   widget honest-null render (§5.2). Independently shippable.
3. **Phase 2 — Performance Context panel:** read-only `PerformanceContextPanel` consuming the
   contract; actual+expected primary chart (gaps, no zero-fill), weather on a separate axis,
   summary cards, data-quality + semantics banner. Labels/states rendered **verbatim**.
4. **Phase 3 — status & deep links:** weather-semantic badges (§6), baseline/Reconciliation +
   Telemetry deep links; compact PH summary variant; company/portfolio reuse.
5. **Phase 4 — conservative narrative:** the variance-tier selector (factual-only; no
   attribution), per audit §D.
6. **Phase 5 — WS.5-aware (out of scope here):** only after WS.5 may
   `used_by_active_model=true` and the "verified model-supported comparison" tier appear.

---

## 10. Browser validation plan (for the build phases)
- **Site 4** against §7: actual curve with honest gaps; observed weather with `unverified`
  labels; weather state `observed_weather_device_no_governed_declaration`; **no POA, no causal
  claim**; missing buckets show the correct `actual_state`, never `0`.
- **Integrity regression (manual):** find/construct a window with a **missing actual** bucket
  and confirm it renders **`N/A`/gap**, while a genuine **`0`** night bucket renders `0`, and a
  **negative tare** value is preserved.
- **State matrix:** exercise each `actual_state` × `expected_state` × weather-semantic
  combination on representative sites/windows; confirm variance is `N/A` when either side is
  missing and `expected` never shows `0`.
- **Timezone/units:** confirm site-tz only affects the "today"/daily boundary; display is
  browser-local; °F/°C toggle is display-only.
- **Deep links** land on the correct Telemetry / Reconciliation / Data Room targets.

---

## 11. Regression tests
**Backend (contract aggregator):**
- Missing-actual bucket → `actual_kw=null`, `actual_state=telemetry_unavailable`,
  `variance_*=null`; **asserts no `0`** is emitted for a missing actual.
- Genuine zero bucket → `actual_kw=0`, `actual_state=no_production_during_interval` preserved.
- Negative tare bucket → value preserved (no clamp).
- Expected states: `missing_inputs`/`pre_pto`/`baseline_invalid`/`baseline_not_available` →
  `expected_*=null` (never 0); `available`/`partial` → variance computed only where valid.
- Period-effective baseline selection unchanged vs `expected_service` (golden compare).
- Weather semantics/eligibility/quality blocks equal the underlying services **verbatim**
  (no re-derivation drift); `source_provenance` ids/metric/agg match the producing rows and are
  `null` (never fabricated) when absent.
- Timezone: `bucket_start_utc` is naive-UTC and equals the rollup key; `bucket_start_site_local`
  matches the `site_timezone` conversion; `site_timezone` changes shift only the daily boundary,
  not point timestamps.
- Auth: asset-view + company-visibility enforced; cross-tenant 404; **zero writes/commits**
  asserted.
**Frontend:**
- Actual Production widget: `null` → `N/A` (snapshot), `0` → `0`, negative → negative; weather
  chip hidden when descriptor absent; "Variance N/A" when a side missing.
- Performance Context panel: gaps render (no zero-fill), labels match contract verbatim, deep
  links resolve.

---

## 12. Modules / behaviors that MUST NOT be changed
- **Expected math & baselines:** `app/services/telemetry/expected_service.py`,
  `baseline_physics_validation.py`, `baseline_from_facts_service.py`,
  `baseline_points_service.py`, `crud/telemetry_expected.py`, the `telemetry_expected_baselines`
  table, and the expected formula/`REQUIRED_PHYSICS_FIELDS`.
- **Weather declaration governance (WS.1–WS.4):** `weather_device_mappings`,
  `declaration_policy`/declaration service, `semantics_reconciliation_service.py`,
  upstream-change detector, and **anything WS.5**.
- **`expected_weather_provenance`** — never written.
- **Ingestion / rollups / scheduler:** `ingestion_service.py`, `rollup_service.py`,
  `scheduler_runner.py`, and the `telemetry_*_interval_rollups` / `telemetry_readings` tables.
- **Device eligibility/classification:** `device_classification.py`,
  `device_eligibility_diagnostics_service.py`; `can_drive_expected` stays frozen to
  `{inverter, module, weather_station}`.
- **Due diligence / reconciliation / `project_facts` / SAFL** as a baseline source.
- **BigQuery / Firestore / legacy telemetry** as operational truth (legacy flag stays off).
- **The site protected mappings** (Site 4) — untouched.

---

## Appendix — open questions / flags for the build sprint
1. **Approve the narrow FE-only integrity fix (§5.2)** independently of the full contract? It
   removes the most visible honesty bug (missing actual → `0`) with the least risk.
2. **Make the O&M section schema `actual`/`irradiance` nullable?** Required for honest actual
   nulls in the *time-series* (vs just the KPI widget). Additive but per-consumer validated.
3. **`actual_state` thresholds** (stale window, `insufficient_data` completeness floor) — pick
   values consistent with the existing readiness/health thresholds; do not invent new ones.
4. **Where does the panel live first** — O&M Site Overview (recommended primary) with a compact
   PH summary variant — and is the contract endpoint under `/api/telemetry/v2/...` (recommended)
   or a new namespace?
5. **Company/portfolio rollups** consume the same contract in a later phase (out of scope now).

**End of design. No production changes were made in this sprint.**
