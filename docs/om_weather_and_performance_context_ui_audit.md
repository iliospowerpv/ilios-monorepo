# O&M Weather, Irradiance & Actual-vs-Expected Performance Context — UI/API Audit & Design

**Status:** Audit / design sprint only — **no production code changes in this sprint.**
**Scope:** Read-only design. This document does **not** implement code, change expected
calculations, alter resolver behavior, revalidate baselines, change weather declarations,
or modify telemetry data.
**Date:** 2026-06-23

---

## 0. Purpose, scope & non-negotiable governance rules

### 0.1 The product gap this sprint addresses
iliOS today exposes, in separate places: V2 actual production telemetry, a weather-adjusted
expected curve, an O&M actual-vs-expected chart, raw irradiance/temperature telemetry for
some sites, and the governed weather-semantics declarations from WS.1–WS.4. **None of these
are presented together** in a single operational view. An operator cannot quickly judge
whether a production variance is plausibly weather-related, telemetry-related, or
operational — and cannot see, in one place, *how trustworthy* each input is.

This audit designs a **read-only "O&M Performance Context"** experience that co-presents
actual production, expected production, observed weather telemetry, weather-source quality,
and variance context **without fabricating causality or overstating unverified weather
semantics.**

### 0.2 Governance rules (binding on every design decision below)
These are restated from the sprint brief and are treated as hard constraints throughout:

1. **Raw observed weather telemetry may be displayed when available.**
2. **`irradiance_wm2` labeling is governed by semantics:**
   - "POA irradiance" **only** when an *active, physics-usable* governed declaration
     establishes POA;
   - otherwise "Observed irradiance" or "Irradiance — semantics unverified."
3. **`cell_temperature_f` labeling is governed by semantics:**
   - "Cell temperature" **only** when governed semantics establish cell/module temperature;
   - otherwise "Observed temperature — semantics unverified."
4. **No causal claims.** Do not imply weather *caused* a variance unless a future,
   explicitly-approved attribution policy exists.
5. **No over-validation.** Do not claim "weather-adjusted" performance is fully validated
   merely because raw weather telemetry is visible.
6. **Keep four things visibly distinct:** raw telemetry, governed declaration state,
   expected-model eligibility, and performance interpretation.
7. **Preserve data integrity:** nulls, genuine zeroes, and small negative nighttime tare
   values are shown honestly — never coerced to 0 or to "good."
8. **No legacy/forbidden sources:** no BigQuery, Firestore, SAFL, or legacy telemetry.

### 0.3 WS.5 boundary
WS.5 (expected-model integration of governed weather) is **deferred**. The UI must therefore
treat governed weather as **context** today, never as a validated input to the active expected
model — until a qualifying declaration **and** WS.5 integration land.

---

## A. Current UI & API audit

### A.0 Headline architectural finding (read this first)
There are **two parallel actual/expected data pipelines**, and **governed, granular weather
lives on only one of them**:

| Pipeline | Endpoints (verified) | Serves | Weather? |
| --- | --- | --- | --- |
| **O&M dashboard charts** | `/api/operations-and-maintenance/sites/{id}/actual-production-chart`, `/actual-vs-expected-chart`, `/past-performance-chart`, `/inverters-performance-chart`; company `/loses-for-a-day-chart`, `/actual-vs-expected-production-chart` | actual_kw, expected_kw, variance %, cumulative, `expected_state` | **Coarse only:** the site `actual-vs-expected-chart` returns a per-period `irradiance` number and the `actual-production-chart` returns a coarse `weather` descriptor (e.g. "Sunny"/"Cloudy" + icon). **No `cell_temperature`, no governed semantics, and the FE renders neither field today.** |
| **V2-native telemetry** | `/api/telemetry/v2/sites/{id}/series`, `/device-series`, `/latest` | rolled-up series for `site_power_ac_kw`, `device_power_ac_kw`, `irradiance_wm2`, `cell_temperature_f` | **Yes (raw rollups only; no expected)** |

**Consequence:** today there is **no single read contract** that returns actual + expected +
*granular, semantics-governed* irradiance + temperature + weather-source quality +
completeness aligned on one time axis. The coarse O&M `irradiance`/`weather` fields exist in
the payloads but are **unused by the UI** and carry **no governed semantics** — they are not a
substitute for the V2 `irradiance_wm2`/`cell_temperature_f` rollups plus the governance layer.
The Performance Context feature is fundamentally a **new read-model that composes these two
pipelines** (plus weather-semantics governance) — it does **not** require new math.

> Verification note: during this audit, exploratory tooling reported several endpoint paths
> that **do not exist** (`/v2/.../expected`, `/v2/.../diagnostics/eligibility`,
> `/v2/.../reconciliation/weather-semantics`). The verified-correct paths are
> `/v2/.../expected-baselines*`, `/v2/.../eligibility-diagnostics`, and
> `/api/weather/sites/{id}/semantics-reconciliation`. All paths in this document were
> confirmed against the router/source on 2026-06-23.

### A.1 Surface-by-surface inventory

Legend for **Value type**: *raw* = stored reading; *rolled-up* = interval mean from the
rollup tables; *modeled* = physics-derived expected; *derived* = computed from the above.

---

#### A.1.1 — O&M "Actual Production" widget (site)
- **Component / route:** `src/modules/operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/ActualProduction/ActualProduction.tsx` → `/operations-and-maintenance/sites/:siteId` and the PH O&M surface.
- **API:** `ApiClient.operationsAndMaintenance.getSiteDashboardProduction(siteId)` → `GET /api/operations-and-maintenance/sites/{siteId}/actual-production-chart` (`OMSiteDashboardProductionResponse`). Freshness via `useSiteLatestTelemetry` → `GET /api/telemetry/v2/sites/{id}/latest`.
- **Metrics & units:** `actual_kw` / `expected_kw` (kW, current); `cumulative_actual_kw` / `cumulative_expected_kw` (kWh, today); `actual_vs_expected`, `cumulative_actual_vs_expected` (%). `expected_kw`/`cumulative_expected_kw` are **nullable**. Also returns `system_size_ac`/`system_size_dc`, `performance_index`, and a coarse `weather: OMSiteWeather | string | null` descriptor (`{ weather_description, weather_icon_url }`, e.g. "Sunny").
- **Time bucket / window:** instantaneous "current" + cumulative "today" (site-local day boundary; see A.2).
- **Timezone:** display via `parseUtc(iso).toLocaleString()` (browser-local). "Today" boundary computed server-side from the **site** timezone.
- **Current labels:** "Production", "Actual (kW)" / "Actual (kWh)", "Expected (kW)" / "Expected (kWh)"; expected tooltip **"Weather Adjusted Projection"**; a coarse weather chip/icon ("Sunny"/"Cloudy"/"Partly cloudy") is rendered from `weather`.
- **Missing/unknown — important nuance:** **expected** is honest: `resolveExpectedState(...)` renders **"N/A" + a reason** (e.g. "Baseline not available"), never `0`. **Actual is NOT:** the widget destructures `actual_kw`, `actual_vs_expected`, `system_size_ac/dc`, and the gauge "rest" segment with `?? 0` (and `weather` defaults to `'Sunny'`), so a missing *actual* renders as `0`, not as "no data". This is a current honesty gap to fix in the Performance Context (B.3 / rule 7), not to copy.
- **Suitability:** Good for KPI cards; **not** a time-series; weather is only a coarse non-governed descriptor → insufficient alone for Performance Context.
- **⚠ Governance note:** the "Weather Adjusted Projection" tooltip implies a validated weather-adjusted model. With WS.5 deferred this is **over-claiming** and should be softened (see C / D).

---

#### A.1.2 — O&M "Actual vs Expected" chart (site)
- **Component / route:** `.../SiteDetails/tabs/Overview/widgets/ActualProjectedPower/ActualProjectedPower.tsx` → `/operations-and-maintenance/sites/:siteId`.
- **API:** `siteActualVsExpectedProduction(siteId)` → `GET /api/operations-and-maintenance/sites/{siteId}/actual-vs-expected-chart` (`OMSiteActualVsExpectedProductionResponse` = `{ data: { period, actual, expected (nullable), irradiance }[], expected_baseline_available, expected_state?, baseline_invalid?, invalid_baseline_id?, baseline_validation_summary?, required_action? }`).
- **Metrics & units:** per-period `actual` (kW), `expected` (kW, **nullable** — null for V2 points), and a coarse `irradiance` (W/m²) value.
- **Value type:** actual = rolled-up; expected = modeled; irradiance = coarse provider value.
- **⚠ Key finding:** the response **already carries `irradiance` per period**, but `ActualProjectedPower.tsx` maps only `actual`, `expected`, and `period` — **`irradiance` is fetched and discarded.** No temperature, and irradiance carries **no governed semantics**, so it cannot be labeled POA (see C).
- **Timezone:** naive-UTC from backend; rendered browser-local.
- **Missing/unknown:** point-level `expected` nulls preserved; `expected_state`/`expected_baseline_available` drive a chart-level note via `resolveExpectedState`; `baseline_invalid` + `invalid_baseline_id` drive a replacement banner with actuals still visible.
- **Suitability:** Closest existing analog to the proposed primary chart, but no rendered weather overlay, no temperature, no governed semantics, and uses the O&M (not V2-native) pipeline.

---

#### A.1.3 — O&M "Past Performance" widget (site)
- **Component:** `.../SiteDetails/tabs/Overview/widgets/PastPerformance/PastPerformance.tsx`.
- **API:** `sitePastPerformance(siteId)` → `GET /api/operations-and-maintenance/sites/{siteId}/past-performance-chart`.
- **Metrics:** historical actual vs expected (kWh) over prior periods; `expected_state` + `expected_baseline_available` consumed by `resolveExpectedState`.
- **Missing/unknown:** honest N/A via the shared resolver.
- **Suitability:** Useful as a "history" tab companion; no weather.

---

#### A.1.4 — O&M "Inverters Performance" chart (site)
- **Component:** O&M Site Overview.
- **API:** `siteInvertersPerformanceData(siteId)` → `GET /api/operations-and-maintenance/sites/{siteId}/inverters-performance-chart`.
- **Metrics:** per-inverter actual production (kW/kWh).
- **Missing/unknown:** prior audit confirmed this surface **does not render N/A as 0%**.
- **Suitability:** Device-mix context; not part of the primary Performance Context but a valid deep-dive.

---

#### A.1.5 — O&M "Losses" widget (company)
- **Component:** `src/modules/operations-and-maintenance/pages/CompanyDetails/tabs/Overview/widgets/Losses/Losses.tsx`.
- **API:** `companyLosesData(companyId)` → `GET /api/operations-and-maintenance/companies/{companyId}/loses-for-a-day-chart` (`OMCompanyDayLosesEntryResponse`).
- **Metrics & units:** cumulative actual, expected, energy loss (kWh).
- **Missing/unknown:** when `expected`/`loss` is null (V2 site/company), it **hides the chart** and shows a text summary + `expectedState` reason. Honest N/A.
- **Suitability:** Company-level context; informs the "compact Project Hub context" placement (F).

---

#### A.1.6 — PH "Device Performance" card (device detail / Overview)
- **Component / route:** `src/modules/project-hub/pages/DeviceDetails/tabs/Overview/components/DevicePerformanceCard/DevicePerformanceCard.tsx` → `/project-hub/companies/:companyId/sites/:siteId/devices/:deviceId`.
- **API:** `ApiClient.telemetryV2.getSiteDeviceRollupSeries(siteId, { deviceId, metric: 'device_power_ac_kw', ... })` → `GET /api/telemetry/v2/sites/{siteId}/device-series`.
- **Metrics & units:** **actual AC power** `device_power_ac_kw` (kW, unit echoed from API).
- **Time bucket / window:** **1h** buckets, **last 24h**.
- **Timezone:** naive-UTC parsed via `dayjs.utc(point.bucket_start).local()`.
- **Labels:** title "Performance"; caption "Last 24 hours · actual AC power (hourly)"; Y-axis "AC Power (<unit>)".
- **Missing/unknown:** explicit "No V2 telemetry readings for this device/window"; always-on caption **"Projected unavailable: per-device expected baseline is not defined."** Never fabricates 0 or a projected series.
- **Suitability:** **The honesty model to emulate.** Already V2-native and gap-correct.

---

#### A.1.7 — PH "Telemetry Readiness" & "Data Health"
- **Component / route:** `src/modules/project-hub/pages/AssetManagementSiteDetails/tabs/Telemetry/Telemetry.tsx` → `/project-hub/companies/:companyId/sites/:siteId/telemetry`.
- **API:** `ApiClient.connections.getTelemetryReadiness(siteId)` and `getTelemetryHealth(siteId)`.
- **Metrics:** Readiness 4-step (Connected → Site mapped → Devices mapped → Data flowing); Health status (`Healthy` / `Warning` / `Error` / `No Data Yet` / `Not Configured`); freshness "Last data: <ts>"; completeness "<mapped>/<eligible> devices mapped"; "Delay: N minutes".
- **Timezone:** `new Date(ts).toLocaleString()` (browser-local).
- **Missing/unknown:** "Never" for null timestamps; "No Data Yet" / "Mapped, No Devices"; "Not Configured" alert.
- **Suitability:** Source for the **telemetry completeness/freshness** summary card and data-quality banner.
- **⚠ Note:** Readiness/health counts key off **`drives_expected`** devices (frozen `{inverter, module, weather_station}`), **not** the broad "mappable" set — so weather sensors that don't drive expected still won't flip health green. The Performance Context banner must say this plainly.

---

#### A.1.8 — PH "Weather Semantics Governance" panel
- **Component:** `.../tabs/Telemetry/WeatherSemanticsPanel.tsx`.
- **API:** `ApiClient.weather.getSemanticsReconciliation(siteId)` → `GET /api/weather/sites/{siteId}/semantics-reconciliation`; `previewUpstreamChanges(siteId)` → `.../device-mappings/upstream-changes`.
- **Metrics/details:** per-device irradiance plane, temperature type, calibration status, governance state (the 9-state taxonomy), `expected_model_eligible`, upstream-drift flag.
- **Labels:** "Weather Semantics Governance", "Weather source present", "Active weather profile", "Expected-eligible"; states/labels/required-actions are rendered **verbatim** from the backend (no FE re-derivation).
- **Missing/unknown:** "Undeclared (unknown)" / "—"; never infers.
- **Suitability:** **Authoritative source of weather-semantic truth** for all Performance Context labels/badges (C). The Performance Context must read from this, never re-derive.

---

#### A.1.9 — PH "Device Eligibility & Diagnostics" panel
- **Component:** `.../tabs/Telemetry/EligibilityDiagnosticsPanel.tsx`.
- **API:** `ApiClient.telemetryV2.getSiteEligibilityDiagnostics(siteId)` → `GET /api/telemetry/v2/sites/{siteId}/eligibility-diagnostics`.
- **Details:** site-level counts (weather sources, meters, gateways); per-device `blocking_level` (`blocks_calculation` / `lowers_confidence` / `informational`) + recommended action; mapping/liveness/semantics indicators.
- **Suitability:** Source for **"why is expected unavailable / weather not used"** explanations and for the data-quality banner's blocking severity.

---

#### A.1.10 — PH "Reconciliation" table (due-diligence provenance)
- **Component / route:** `.../tabs/Reconciliation/components/ReconciliationTable.tsx` → `/project-hub/companies/:companyId/sites/:siteId/reconciliation`.
- **API:** `ApiClient.reconciliation.getSiteReconciliation(siteId)` → `GET /api/due-diligence/sites/{siteId}/reconciliation`.
- **Details:** provenance ladder per canonical field (uploaded doc → AI value → accepted key → candidate/active fact → draft/active baseline → design points); columns "AI value / Accepted / Active fact / Draft baseline / Active baseline / Legacy".
- **Suitability:** **Baseline provenance** source and the deep-link target for "baseline invalid / inputs missing" data-quality issues (F). This is the **physics-assumption** provenance, distinct from **weather-semantic** provenance (A.1.8).

---

#### A.1.11 — PH "Devices" grid
- **Component / route:** `.../tabs/Devices/Devices.tsx` → `/project-hub/companies/:companyId/sites/:siteId/devices`.
- **API:** `ApiClient.assetManagement.devices(siteId, …)` (server-side paged, `categories` filter) merged with `getSiteEligibilityDiagnostics(siteId)` (via `src/utils/telemetry/deviceDiagnostics.tsx`).
- **Details:** capacity (kW), eligibility chip, telemetry-status chip; CSV export of all matching rows.
- **Suitability:** Navigation source to device-level deep-dive; not a primary Performance Context surface.

---

#### A.1.12 — Company- & portfolio-level actual/expected surfaces (scoped out, listed for completeness)
These roll up the same `expected_state`/`resolveExpectedState` honesty model at company/portfolio
scope. The Performance Context panel in this design is **site-level**; these are **out of scope**
for the panel itself but are the natural consumers of the compact summary (F) in a later phase:
- **O&M Company "Actual Production"** — `.../CompanyDetails/tabs/Overview/widgets/ActualProduction` → `getCompanyDashboardProduction(companyId)` → `/api/operations-and-maintenance/companies/{id}/actual-production-chart` (`OMCompanyDashboardProductionResponse`: totals, `total_expected_kw` nullable, `expected_state`).
- **O&M Company "Production vs Projected"** — `.../CompanyDetails/tabs/Overview/widgets/ProductionProjected` → `companyActualVsExpectedProductionData(companyId)` → `/api/operations-and-maintenance/companies/{id}/actual-vs-expected-production-chart` (per-site `{ actual_kw, expected_kw, size }`, all nullable; bubble chart).
- **PH Company "Performance" tab** — `.../AssetManagementCompanyDetails/tabs/Performance/Performance.tsx` reuses the same company actual-vs-expected widget.
- **My Portfolio "Companies" widget** — `.../my-portfolio/pages/PortfolioPage/components/Companies.tsx` consumes `resolveExpectedState` to gate the expected column.
- **None of these render irradiance/temperature or governed weather semantics** — the weather gap is identical to the site surfaces.

---

### A.2 Cross-cutting backend data-contract facts (verified)

- **Actual series (site):** `GET /api/telemetry/v2/sites/{id}/series` → rolled-up `site_power_ac_kw` (kW), buckets `15m|30m|1h|1d`, **mean** aggregate, **naive-UTC** timestamps, from `telemetry_site_interval_rollups`.
- **Actual series (device):** `GET /api/telemetry/v2/sites/{id}/device-series` → `device_power_ac_kw`.
- **Irradiance/temperature series:** same `/series` (+`/device-series`) endpoints with `normalized_metric=irradiance_wm2` (W/m²) or `cell_temperature_f` (°F) — **rolled-up means of raw observations**; the *metric name does not assert semantics*.
- **Latest/freshness:** `GET /api/telemetry/v2/sites/{id}/latest`.
- **Expected (modeled):** computed by `app/services/telemetry/expected_service.py` (`compute_expected_buckets` → `ExpectedResult`). Surfaced through the O&M `…-chart` endpoints (FE) and the baseline endpoints `GET /api/telemetry/v2/sites/{id}/expected-baselines`, `/expected-baselines/active`, `/expected-baseline/readiness-from-facts`, `POST /expected-baseline/create-draft-from-facts`. **There is no `/expected` time-series endpoint.**
- **Expected formula:** `expected_power_kw = min(dc_nameplate_kw * total_derate, ac_nameplate_kw)`; physics inputs `REQUIRED_PHYSICS_FIELDS` = `module_wattage`, `module_quantity`, `inverter_wattage`, `inverter_quantity`, `thermal_coefficient_pct`, `power_tolerance_min_pct`, `year_1_degradation_pct`, `annual_degradation_pct`, `cec_efficiency_pct` (only a subset are fact-backed; datasheet constants supplied at draft creation).
- **Expected resolves to `null` (never 0)** for `missing_inputs`, `pre_pto`, `baseline_invalid`, `baseline_not_available` (see C/D state table).
- **WeatherResolver W1** (`app/services/weather/weather_resolver.py`): read-only, **DAS-only**; a window is `semantics_verified` **only** if a mapping declares irradiance plane = `poa` **and** temperature type ∈ `{cell, module, modeled_cell}`, with **no conflict** and **full window coverage**; otherwise it falls back to `legacy_das_unverified` and semantics stay `unknown`. **W1 never transposes GHI→POA or ambient→cell.**
- **Timezone rule:** readings/rollups are stored **naive-UTC**; the **site** timezone (IANA, `Site.timezone`) is used **only** for the site-local "today"/day boundary in rollup queries — **never for display.** All display is **viewer browser-local**.
- **Completeness/freshness:** computed in `rollup_service.py` via **per-series cadence inference** (median sample gap) → received/expected ratio; freshness from `TelemetrySyncJob` / latest reading.

---

## B. Proposed "Performance Context" layout (site-level, read-only)

A single site-level O&M component, **`PerformanceContextPanel`** (proposed), composed of four
stacked regions. It is **read-only** and composes existing endpoints (A.0) plus a proposed
thin aggregator (G.2).

### B.1 Primary chart — Power (actual vs expected)
- **Series:** Actual AC power (kW) [V2 `site_power_ac_kw`, rolled-up] + Expected AC power (kW)
  [modeled, nullable].
- **Time-window selector:** Today / 24h / 7d / 30d / custom; bucket auto-selected
  (`15m`→`1h`→`1d`) to keep point counts sane.
- **Expected-state label (chip on the chart header)** — exactly one of:
  - **Available** — full expected curve shown.
  - **Partial** — expected shown only where present + "partial coverage" note.
  - **Baseline invalid for period** — active baseline failed fail-closed physics validation;
    expected suppressed (null), actual still shown.
  - **Baseline unavailable** — no active baseline; expected = N/A.
  - **Weather inputs missing** — `expected_service` returned `missing_inputs` because the
    irradiance **or** cell-temperature *value* was absent for the bucket (expected = null).
- **Important — do NOT conflate semantics with availability:** unverified weather *semantics*
  do **not** suppress expected today. `WeatherResolver` passes raw DAS values through under
  `legacy_das_unverified` (semantics stay `unknown`, expected math is unchanged); only an
  *absent value* yields `missing_inputs`. The "semantics unverified" condition is therefore a
  **governance/context status (B.4 banner)**, NOT an expected-state cause. Surfacing it as an
  expected-state would misrepresent current behavior (and pre-empt WS.5).
- **Gaps:** missing buckets render as **gaps**, never zero-filled; genuine zeroes and small
  negative nighttime tare are preserved.

### B.2 Weather context — irradiance & temperature (aligned, separate axis)
- **Series:** Observed irradiance (W/m²) + Observed temperature (°F/°C per user pref).
- **Layout rule (hard):** **never** force weather and power onto the same Y-axis. Use a
  **separate secondary axis or an aligned subplot / synchronized panel** sharing the X axis
  with B.1.
- **Labels are semantics-governed** (see C): default to "Observed irradiance / Observed
  temperature — semantics unverified" until a qualifying active declaration upgrades them.
- **Gaps preserved** for missing values.

### B.3 Performance summary cards
1. Actual energy for selected period (kWh).
2. Expected energy where available (kWh) — else honest N/A + reason.
3. Variance (kWh and %) — only when expected is `available`/`partial`; else "Variance N/A
   (expected unavailable)".
4. Observed peak irradiance (W/m²) — labeled per semantics.
5. Weather source status — from semantics reconciliation (the 9-state headline).
6. Baseline status / source — active / draft / invalid / unavailable + provenance deep link.
7. Telemetry completeness / freshness — "<mapped>/<eligible> mapped", "Last data: <ts>",
   completeness %.

### B.4 Data-quality & semantics banner (one composed strip)
Reads from semantics reconciliation + eligibility diagnostics + expected-state, and renders
the **most severe** applicable message(s), e.g.:
- "Observed irradiance is available, but sensor semantics are not yet verified."
- "Expected comparison is partially available because the historical baseline is invalid."
- "Weather source is governed and eligible for the expected model; model integration is pending (WS.5)." *(only when a qualifying active declaration exists; never claim "model-used" pre-WS.5)*
- "Weather telemetry is unavailable for this period."
- "Actual production is available; expected comparison is unavailable."

**The four-way separation (rule 6) is the panel's organizing principle:** B.1/B.2 = raw +
modeled telemetry; B.3 cards 5–6 = governed declaration + baseline state; B.3/B.4 =
expected-model eligibility; B.4 + D = interpretation. None bleeds into another.

---

## C. Weather-semantic display rules (labels & badges)

All labels derive from the **semantics reconciliation** response (A.1.8) — never re-derived
client-side. "Used by active expected model" is true **only** when
`expected_model_eligible === true` **and** WS.5 is integrated; **today that flag never makes
the Performance Context claim "used"** because WS.5 is deferred (it shows "Eligible —
integration pending" at most).

### C.1 Irradiance
| Condition (governed) | Label | Badge | "Used by model?" |
| --- | --- | --- | --- |
| Active, physics-usable, plane = POA | **POA irradiance** | `POA · governed` (success) | Eligible (pending WS.5) |
| Active, governed, plane = GHI/other | **GHI irradiance (governed)** | `GHI · governed` (info) | Contextual |
| Observed, no/!active declaration | **Observed irradiance — semantics unverified** | `unverified` (warning) | Contextual |
| No irradiance device/source | **Irradiance source missing** | `no source` (neutral) | — |

### C.2 Temperature
| Condition (governed) | Label | Badge | "Used by model?" |
| --- | --- | --- | --- |
| Active, type ∈ {cell, module, modeled_cell} | **Cell/Module temperature** | `cell · governed` (success) | Eligible (pending WS.5) |
| Active, governed, type = ambient | **Ambient temperature (governed)** | `ambient · governed` (info) | Contextual |
| Observed, no/!active declaration | **Observed temperature — semantics unverified** | `unverified` (warning) | Contextual |
| No temperature device/source | **Temperature source missing** | `no source` (neutral) | — |

### C.3 Declaration / source lifecycle badges (mirror the 9-state taxonomy)
| Taxonomy state | Badge text | Severity (from `blocking_level`) |
| --- | --- | --- |
| `observed_weather_device_no_governed_declaration` | "Observed — no governed declaration" | lowers confidence |
| `source_exists_semantics_unknown` | "Source present — semantics undeclared" | lowers confidence |
| `declaration_draft` | "Declaration draft — not activated" | lowers confidence |
| `declared_not_physics_usable` | "Declared — not physics-usable" | lowers confidence |
| `declared_eligible_integration_pending` | "Eligible — integration pending" | informational |
| `declaration_stale_needs_re_review` | "Active — needs re-review" | lowers confidence |
| `weather_source_missing` | "No weather device or source" | lowers confidence |
| `weather_source_stale` | "Weather source not active" | lowers confidence |
| `source_coverage_incomplete` | "Source coverage incomplete" | lowers confidence |
| *(modeled/design weather)* | "Modeled / design weather" | informational |
| *(no telemetry at all)* | "No weather telemetry" | neutral |

### C.4 What the UI must always reveal (per weather row / tooltip)
- **Declaration basis** (e.g. source document / provider confirmed / reviewer assumption).
- **Evidence / source state** (present, draft, stale, missing).
- **Expected-model eligibility** (`expected_model_eligible`).
- **Whether the data is actually used by the active expected model** — **today: never "used";
  at most "eligible, integration pending (WS.5)".**
- **Whether the data is merely contextual.**

---

## D. Variance interpretation policy (conservative)

### D.1 Allowed statements (factual, source-backed)
- "Observed irradiance was lower during the selected interval."
- "Actual production was below modeled expected."
- "Weather telemetry is unavailable / semantically unverified."
- "A production device was not reporting."

### D.2 Not allowed (without a future, explicit attribution policy)
- "Cloud cover caused underperformance."
- "Irradiance explains the production shortfall."
- "The site is underperforming because of weather."
- Any causal / root-cause conclusion from correlation alone.

### D.3 Four interpretation tiers (the narrative ladder)
| Tier | When it applies | Allowed language template |
| --- | --- | --- |
| **No inference** | weather unverified, or expected unavailable | "Actual was X. Expected/weather context is unavailable or unverified; no comparison is asserted." |
| **Possible contextual signal** | both actual and *observed* weather present, semantics still unverified | "Actual was below modeled expected; observed irradiance was also lower in the same interval. Sensor semantics are unverified, so this is contextual only — not an attribution." |
| **Verified model-supported comparison** | expected `available` **and** weather `expected_model_eligible` **and** WS.5 integrated | "Actual was X vs weather-adjusted expected Y (variance Z%). Weather inputs are governed and used by the active model." *(blocked until WS.5)* |
| **Operational investigation needed** | device not reporting / completeness low / baseline invalid | "A production device was not reporting / data completeness was low for this interval; investigate telemetry before drawing performance conclusions." |

**Rule:** the panel selects the *highest tier the evidence actually supports* and never
borrows language from a higher tier. Correlation visuals (B.2 aligned to B.1) are permitted;
correlation **captions** are not.

---

## E. Site 4 (110 Shawmut) design validation

Site 4 is the canonical validation case (it is the protected telemetry-mapping site; this
sprint touches **no** mappings).

The Performance Context for Site 4 must show:
- **Actual site power curve** — V2 `site_power_ac_kw` rollups (real data).
- **Expected site power curve where available** — modeled; otherwise honest expected-state
  chip.
- **Observed irradiance** and **observed temperature** — raw V2 rollups, labeled
  **"Observed … — semantics unverified."**
- **Weather-dependency status banner (exact):**
  > "Observed weather telemetry is available, but IMT Reference Cell semantics are not yet
  > governed/verified."
- **No POA claim, no causal claim.** Irradiance is **not** labeled POA and weather is **not**
  asserted to explain any variance, because Site 4 has **no qualifying active declaration**
  and **WS.5 is not integrated**.

Expected acceptance for Site 4: the panel renders actual + observed weather together, every
weather label carries the `unverified` badge, the expected chip reflects the true baseline
state, and the narrative stays in Tier "No inference" / "Possible contextual signal" only.

---

## F. Reporting & navigation

| Placement | Role | Notes |
| --- | --- | --- |
| **O&M Site Overview** | **Primary home** of the full Performance Context panel | Adjacent to existing actual-vs-expected widgets |
| **Project Hub O&M summary** | **Compact** context (key cards + banner, link to full panel) | Reuse summary cards B.3 only |
| **Reconciliation deep link** | jump to baseline/physics-assumption data-quality issues | `/project-hub/.../reconciliation` (A.1.10) |
| **Telemetry tab deep link** | jump to weather-source semantics governance | `/project-hub/.../telemetry` → Weather Semantics panel (A.1.8) |
| **Data Room deep link** | jump to source evidence for a declaration/assumption | gated to statuses whose next step is in the Data Room |
| **Investor report (future)** | disclosure / **context** only | never unsupported attribution; reuse D tiers and C labels verbatim |

Deep-link rule: a status whose next action happens elsewhere shows a working link; a status
whose next action is local (e.g. baseline activation) shows the action text **without** a dead
link (mirrors the existing reconciliation `StatusCell` pattern).

---

## G. Test & implementation plan

### G.1 UI state matrix (primary chart × weather × expected × quality)
| # | Actual | Expected state | Weather telemetry | Weather semantics | Banner / behavior |
| --- | --- | --- | --- | --- | --- |
| 1 | present | `available` | present | unverified | "Observed weather present; semantics unverified" + Tier "possible contextual signal" |
| 2 | present | `available` | present | eligible (+WS.5) | "Weather governed & model-used" + Tier "verified comparison" *(post-WS.5 only)* |
| 3 | present | `baseline_invalid` | present | any | expected suppressed (null); "Baseline invalid for period"; actual + weather still shown |
| 4 | present | `baseline_not_available` | present | any | "Baseline unavailable"; variance N/A |
| 5 | present | `missing_inputs` (irradiance/cell-temp **value** absent) | absent for those buckets | any | "Weather inputs missing"; expected null where absent; variance N/A |
| 6 | present | `pre_pto` | present | any | "Pre-PTO — no expected yet" |
| 7 | present | any | **absent** | n/a | "Weather telemetry unavailable for this period" |
| 8 | **absent** | any | any | any | "No V2 telemetry readings for this window"; no fabricated 0 |
| 9 | partial | `partial` | partial | any | gaps preserved on both axes; "partial coverage" notes |
| 10 | present (device not reporting subset) | any | any | any | Tier "operational investigation needed" |

### G.2 API / data-contract requirements
- **New read-only aggregator (proposed), Phase 1:** `GET /api/telemetry/v2/sites/{id}/performance-context?window=&bucket=&temp_unit=` returning, on one aligned time axis:
  - `actual_power_kw[]` (rolled-up), `expected_power_kw[]` (modeled, nullable) + `expected_state`;
  - `irradiance_wm2[]`, `temperature[]` (with `temp_unit`), **each with a `semantics` block** (label, plane/type, basis, `expected_model_eligible`, `used_by_active_model: false` until WS.5);
  - `summary` (actual/expected energy, variance kWh/%, peak irradiance);
  - `weather_status` (9-state headline + blocking level), `baseline_status` (+provenance ids),
    `completeness`/`freshness`.
- **Composition, not new math:** the aggregator **only reads** existing rollups + `expected_service` + `semantics_reconciliation_service` + `eligibility_diagnostics` + readiness/health. **No writes/commits.** Never calls activate/promote/revalidate.
- **Null discipline:** nulls, genuine zeroes, negative tare preserved end-to-end; expected null never coerced to 0.
- **Timezone/unit rules:** timestamps naive-UTC over the wire, rendered browser-local; site-tz only affects "today" boundary; temperature unit follows user preference (°F default), conversion display-only.

### G.3 Charting approach
- Reuse the existing chart stack (Chart.js, as in DevicePerformanceCard/ActualProduction).
- Power on primary Y; weather on a **separate** Y-axis or **synchronized subplot** sharing X
  (B.2 hard rule). `spanGaps: false` so missing buckets are visible gaps.

### G.4 Accessibility
- Don't encode state by color alone — pair every badge/chip with text (C tables).
- Chart series have text/table fallbacks; banner messages are real text (screen-reader
  friendly); tooltips keyboard-reachable; contrast meets WCAG AA (note the MUI
  `primary.main` legibility caveat for headers on filled surfaces).

### G.5 No-data / partial-data behavior
- Per G.1 rows 7–9: explicit honest copy, gaps preserved, no zero-fill, no fabricated series.
- Device-not-reporting subset → Tier "operational investigation needed" (D.3).

### G.6 Browser validation plan (when a later build phase runs)
- Validate Site 4 against E (observed weather + unverified labels + correct banner, no POA,
  no causal claim).
- Exercise each G.1 row on representative sites/windows; confirm gaps render and N/A never
  shows as 0; confirm timezone (site "today" vs browser-local display) and °F/°C toggle.
- Confirm deep links land on the correct Telemetry / Reconciliation / Data Room targets.

### G.7 Phased implementation plan
1. **Phase 1 — read-only data contract:** the `performance-context` aggregator (G.2),
   composition-only, fully tested against the existing services. No UI.
2. **Phase 2 — O&M chart/context UI:** `PerformanceContextPanel` (B.1–B.4) on O&M Site
   Overview, labels/states rendered verbatim from the contract.
3. **Phase 3 — status & deep-link integration:** wire C badges + F deep links; compact PH
   summary variant.
4. **Phase 4 — conservative narrative/insight rules:** implement the D tier selector
   (factual-only language; no attribution).
5. **Phase 5 — WS.5-aware expected-model connection:** *only after WS.5* allow the "verified
   model-supported comparison" tier and "used by active model = true".

---

## Appendix — open questions / flags for the build sprint
1. **Soften "Weather Adjusted Projection" tooltip** (A.1.1) — currently over-claims a
   validated weather-adjusted model while WS.5 is deferred. Recommend "Modeled expected
   (weather inputs not yet governed)".
2. **Two-pipeline consolidation:** decide whether Performance Context standardizes the
   actual/expected source on the V2-native series (recommended) vs. the O&M `…-chart`
   endpoints. The aggregator (G.2) lets the panel use one consistent source.
3. **"Semantics unverified" is a governance/context banner, not an expected-state.** Current
   behavior: `WeatherResolver` passes raw DAS values through under `legacy_das_unverified`
   (expected math unchanged); `expected_service.missing_inputs` fires only when an
   irradiance/cell-temp *value* is absent. The aggregator therefore reports the W1 verification
   verdict as a **banner status** (B.4) alongside, but separate from, the expected-state — it
   must NOT be folded into `missing_inputs`. No new math, no behavior change.
4. **Readiness/health vs. weather eligibility mismatch** (A.1.7): weather sensors that don't
   drive expected won't turn health green; the banner must explain this so operators don't
   read "warning" as a weather outage.

**End of audit. No production changes were made in this sprint.**
