# Native Weather Indicator Replacement for Weatherstack — Audit & Design

> **Type:** Audit / design sprint — **READ-ONLY**. No production code, schema,
> migration, route, scheduler, or config was changed. The sole artifact is this
> document.
> **Date:** 2026-06-26.
> **Objective:** Design a native iliOS replacement for the **paid Weatherstack
> cosmetic weather indicator** (description + icon) shown on the site Performance
> Overview widget and on site-card lists, using **existing iliOS data only** and
> **never fabricating** a weather condition.
> **Companion:** `docs/weather_data_source_audit.md` (the upstream source audit
> this design builds on — read §1, §10, §15–§16 there for the Weatherstack
> pipeline and the data-integrity boundaries).

---

## 0. Scope guardrails (restated)

In scope (design only):
- Trace current UI consumers of the cosmetic weather indicator.
- Design a native derived "observed condition" using existing iliOS telemetry.
- Define display states, fallback/null states, affected files, testing, browser
  validation, and the eventual Weatherstack decommission path.

Out of scope (hard constraints honored by this document):
- **No Weatherstack removal yet**, **no production code changes**, **no provider
  integration**, **no new paid API**, **no expected-model changes**, **no
  baseline math changes**, **no weather-semantics changes**, **no WS.5**, **no
  migrations unless explicitly justified** (none are required for the core
  design; one optional additive column is noted and deferred — see §7).

---

## 1. Current UI impact

### 1.1 What renders today

The cosmetic indicator is a small 32×32 image (or a fallback MUI `WbCloudy`
cloud icon) plus a tooltip carrying a free-text weather **description**. Its only
inputs are the two Weatherstack-sourced fields written into `sites_weather`:
`weather_description` and `weather_icon_url` (surfaced on a site via
`Site.latest_weather_info` — see the source audit).

### 1.2 Exact consumers

| # | Surface | File | What it reads | What it shows |
| --- | --- | --- | --- | --- |
| 1 | **Shared component** | `src/components/common/WeatherIndicator/WeatherIndicator.tsx` | `imageSrc: string \| null` | Renders the icon image; falls back to `WbCloudy` when `imageSrc` is null/`'N/A'`/`DEMO_*`; shows a spinner while the image loads |
| 2 | **Site Performance Overview widget** | `…/operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/ActualProduction/ActualProduction.tsx` | `weather` (string-or-object) → `weatherDescription`, `weatherIconUrl` | `BootstrapTooltip` titled **"Observed weather (contextual): {description}"** wrapping `<WeatherIndicator imageSrc={weatherIconUrl} />` |
| 3 | **Company → Sites list** | `…/operations-and-maintenance/pages/CompanyDetails/tabs/Sites/Sites.tsx` | `value?.weather_description`, `value?.weather_icon_url` | Per-row tooltip + `<WeatherIndicator imageSrc=… />` (header cell uses `imageSrc={null}`) |
| 4 | **My Portfolio → Sites list** | `…/my-portfolio/pages/PortfolioPage/components/Sites.tsx` | `value?.weather_description`, `value?.weather_icon_url` | Same per-row pattern as #3 |
| 5 | **API types** | `src/api/operations-and-maintenance.ts` | `OMSiteWeather { weather_description: string; weather_icon_url: string }` (FE type; the backend Pydantic equivalent is `WeatherSchema` in `app/schema/om_site.py`) | Type only |
| 6 | **Tests** | `…/WeatherIndicator/__tests__/WeatherIndicator.test.tsx`, `…/ActualProduction/__tests__/ActualProduction.test.tsx` | fixtures `weather_description`/`weather_icon_url` | — |

**Note on the "Performance Dashboard":** the user-described indicator lives in the
O&M **Site Details → Overview** `ActualProduction` widget (surface #2) and the two
site-card lists (#3, #4). There is no separate dedicated weather page. The native
V2 Telemetry tab already has a richer, honest weather block
(`PerformanceContextPanel`) — that panel is **not** a Weatherstack consumer and is
left untouched; it is, however, the data model this design reuses (see §2).

### 1.3 Impact of replacement
- All three visible surfaces (#2, #3, #4) and the shared component (#1) change
  from "image + free-text description" to a **derived condition state + honest
  label**. The shape of the data the FE consumes changes (icon URL/description →
  a small typed condition object), so the API types (#5) and tests (#6) change.
- No other part of the app reads `weather_description`/`weather_icon_url`
  (confirmed by repository search), so blast radius is limited to the table above.

---

## 2. Available native data sources

All of the following already exist in `backend/ilios-server` and require **no new
provider, secret, or external call**.

| Source | Where | Useful fields | Honesty caveat |
| --- | --- | --- | --- |
| **Native rollup actuals** | `TelemetrySiteRollupCRUD.get_series` (`telemetry_site_interval_rollups`) | `irradiance_wm2` (normalized metric `IRRADIANCE_METRIC`), `cell_temperature_f` (`CELL_TEMPERATURE_METRIC`), site power, `bucket_start`, `sample_count`, `completeness` | The normalized `irradiance_wm2` metric **merges POA and GHI** (`Sun→GHI`, `Sun2→…` both normalize into one key), so the **plane of the raw value is unknown** unless governed. Treat raw irradiance as an *uncalibrated light level*, never as POA. |
| **performance-context envelope** | `GET /api/telemetry/v2/sites/{id}/performance-context` → `build_performance_context` (`services/telemetry/performance_context_service.py`) | `series[].irradiance_wm2`, `series[].temperature`, `series[].bucket_start_site_local`, `series[].actual_state`; `telemetry_quality.freshness_state` (`fresh`/`stale`/`no_data`) + `latest_reading_at`; `weather_semantics` (governed plane/type + `expected_model_eligible` + `headline_state`) | Read-only, composition-only; already enforces the **0-vs-null** rule (null = unavailable, 0 = measured zero). Ideal single source for the single-site widget. |
| **WeatherResolver output** | `services/weather/weather_resolver.py` (`ResolvedWeatherBucket.irradiance_poa_wm2`, `.cell_temperature_f`; `ResolvedWeatherWindow`; status `semantics_verified` / `legacy_das_unverified` / `missing_irradiance` / `missing_cell_temperature`) | Irradiance + cell-temp values (under W1 these are the **existing DAS rollup values, untouched**); plane/type labeled only when governed; explicit status enums | Governed/physics seam. Under W1 the resolver does **not** null ungoverned values — it passes the DAS values through with status `legacy_das_unverified` and `unknown` plane/temp (**null means *missing rows***, not "ungoverned"); it reaches `semantics_verified` only with a governed declaration. Use it **only** to decide whether we may say "POA/cell" — **not** to drive the cosmetic icon (the icon reads the raw rollup irradiance directly). |
| **Governed weather declarations** | `weather_device_mappings` via the semantics reconciliation embedded in `weather_semantics` | `irradiance_plane`, `temperature_type`, `expected_model_eligible`, `declaration_basis` | The **only** authority that lets the UI say a value is POA/cell. Default is `unknown`; never auto-promote. |
| **Site metadata** | `models/site.py` | `timezone` (clean IANA `VARCHAR`, NOT NULL, default `UTC`), `lon_lat_url` (a **VARCHAR URL** — the only geo field; **no numeric latitude/longitude columns exist**) | Timezone is reliable for local-time night detection. Lat/long must be **parsed out of the URL** (fragile) or the design degrades gracefully without it. |
| **Demo telemetry** | demo pipeline (`is_demo` sites) | Same `irradiance_wm2`/power metrics, simulated | Demo irradiance is real telemetry within the demo pipeline; the derivation treats it identically (no special weather fabrication). The existing `DEMO_` icon special-case disappears with the icon. |

**Key data limitation that shapes the algorithm:** we have reliable **timezone**
but **no reliable numeric lat/long**, and the raw irradiance **plane is unknown**.
Therefore the design must (a) derive condition primarily from **observed
irradiance magnitude + site-local time**, (b) treat the result as an *observed
light level / contextual condition*, never a calibrated meteorological reading,
and (c) only escalate to a true clear-sky "sunny vs cloudy" classification when
lat/long can be resolved (Tier A below).

---

## 3. Proposed derivation algorithm

### 3.1 Design principles
1. **Never fabricate.** No reading ⇒ "unavailable", never a guessed condition and
   never a `0` rendered as a real value.
2. **Observed ≠ governed.** The indicator is an *observed light level* derived
   from raw telemetry; it must be visually and textually distinct from the
   governed weather-semantics block. It must **not** imply POA/cell unless a
   governed declaration says so.
3. **No rain claims.** Rain is not detectable from irradiance; very low daytime
   irradiance is reported as **"overcast / precipitation (undetermined)"** — the
   honest reading of the requested `rainy-unknown` state.
4. **Confidence is explicit.** Each result carries a `confidence`
   (`observed_calibrated` / `observed_uncalibrated` / `coarse` / `unavailable`)
   and an `as_of` timestamp.

### 3.2 Inputs (per site, per window — default last 24h, latest non-null bucket)
- `irr = ` latest non-null `irradiance_wm2` in the window (and the bucket's
  `bucket_start_utc` / `bucket_start_site_local`).
- `local_hour = ` hour from `bucket_start_site_local` (via site `timezone`).
- `freshness = telemetry_quality.freshness_state` (`fresh`/`stale`/`no_data`).
- `plane_governed = weather_semantics.irradiance.plane == 'poa' AND expected_model_eligible`
  (governed authority flag — used only for labeling/confidence, not for the icon).
- `latlon = parse(lon_lat_url)` if resolvable, else `None`.
- Optional: latest `temperature` + its governed `temperature_type` (supplementary
  chip only; never used to classify the sky).

### 3.3 Tiered classification

**Tier A — Approximate clear-sky index (only when `latlon` resolves).**
Compute solar zenith `Z` for `(lat, lon, timestamp)` with a pure-Python solar
position routine (no external lib/API). Compute a clear-sky GHI reference with a
simple closed-form model (e.g. Haurwitz: `GHI_cs = 1098·cos(Z)·exp(-0.057/cos(Z))`
for `cos(Z) > 0`, else 0). Define an **approximate** clear-sky index
`kt = irr / GHI_cs`:

> ⚠️ **This is an observed-light classifier, not calibrated meteorology.** The
> clear-sky reference is GHI while the observed `irradiance_wm2` may be POA *or*
> GHI (plane unknown unless governed), so `kt` is *indicative*, not exact. A truly
> calibrated index would need a **plane-aware** clear-sky reference (GHI↔POA
> transposition), which is deliberately **out of scope** (it would touch physics).
> Tier A labels therefore stay phrased as approximate/observed.

| Condition | Rule | State | Label |
| --- | --- | --- | --- |
| Sun below horizon | `cos(Z) ≤ 0` (or `Z ≥ ~90°`) | `nighttime` | "Nighttime" |
| Sun up, very low | `0 < elevation < ~5°` | `low_light` | "Low light (dawn/dusk)" |
| Clear | `kt ≥ 0.75` | `sunny` | "Sunny / clear" |
| Mixed | `0.4 ≤ kt < 0.75` | `partly_cloudy` | "Partly cloudy" |
| Overcast | `kt < 0.4` (daytime) | `cloudy` | "Cloudy / overcast" |
| Very low daytime | `kt < 0.15` with sun well up | `overcast_unknown` | "Overcast / precipitation (undetermined)" |

**Tier B — Irradiance magnitude + local-time bands (when `latlon` is missing).**
No clear-sky reference is available, so we report a coarser *observed light level*
and only assert night via local time:

| Condition | Rule | State | Label |
| --- | --- | --- | --- |
| Dark + night hours | `irr ≤ 5 W/m²` AND `local_hour` in night band (e.g. 20:00–05:00) | `nighttime` | "Nighttime" |
| Dark, daytime hours | `irr ≤ 5 W/m²` AND daytime hours | `low_light` | "Low light / dark (undetermined)" |
| Strong light | `irr ≥ 600 W/m²` | `sunny` | "Strong sunlight (observed)" |
| Moderate light | `150 ≤ irr < 600` | `partly_cloudy` | "Moderate light (observed)" |
| Low light | `5 < irr < 150` daytime | `cloudy` | "Low light / overcast (observed)" |

> Tier B thresholds are coarse and latitude/season-naïve **by design** — they
> describe *observed light*, not certified sky state, and the label wording makes
> that explicit ("observed"). Tier A is preferred wherever lat/long resolves.

**Common overrides (both tiers):**
- `freshness == no_data` OR no non-null `irr` in window ⇒ `unavailable` →
  "Observed weather unavailable".
- `freshness == stale` ⇒ keep the derived state but downgrade `confidence` to
  `coarse` and append "(last seen {as_of})"; if also no `irr`, ⇒ `unavailable`.

### 3.4 Confidence & labeling
- `confidence = observed_calibrated` denotes only that the **irradiance plane is
  governed** (we may then add "(governed POA)") — it does **not** assert
  meteorological calibration, because even Tier A compares against a GHI clear-sky
  reference. Otherwise `observed_uncalibrated` (Tier A, ungoverned plane) or
  `coarse` (Tier B / stale).
- The tooltip **always** states the basis: e.g. *"Observed light level
  (uncalibrated telemetry) — {label}, as of {site-local time}."* It **never**
  says POA/cell/temperature semantics unless governed.

### 3.5 Output contract (typed, additive)
```
NativeWeatherCondition {
  state: 'sunny' | 'partly_cloudy' | 'cloudy' | 'overcast_unknown'
       | 'low_light' | 'nighttime' | 'unavailable'
  label: string                 // honest human caption
  light_level: 'strong' | 'moderate' | 'low' | 'dark' | null
  observed_irradiance_wm2: number | null
  plane_governed: boolean       // true only if governed POA
  temperature: { value: number, unit: 'F'|'C', type: string|null } | null
  confidence: 'observed_calibrated' | 'observed_uncalibrated' | 'coarse' | 'unavailable'
  as_of_utc: string | null
  as_of_site_local: string | null
  data_quality: 'fresh' | 'stale' | 'no_data'
}
```
Icon mapping (MUI, no remote images): `sunny→WbSunny`, `partly_cloudy→`
(part-sun, e.g. `WbCloudy` tinted)`, `cloudy→Cloud`, `overcast_unknown→Grain`
(or `Umbrella`), `low_light→WbTwilight`, `nighttime→DarkMode`/`NightsStay`,
`unavailable→CloudOff` with neutral styling.

---

## 4. Fallback / null states

| Situation | State | Rendered |
| --- | --- | --- |
| No irradiance reading at all in window | `unavailable` | `CloudOff` + tooltip "Observed weather unavailable" |
| `freshness_state == no_data` / telemetry not configured | `unavailable` | same |
| Telemetry stale but a last reading exists | derived state, `confidence: coarse` | icon + "(last seen {as_of})" |
| Daytime but irradiance ≈ 0 (sensor outage vs heavy weather — indistinguishable) | `low_light` (Tier B) / `overcast_unknown` (Tier A) | honest "undetermined" wording, **never "rainy"** |
| Lat/long unresolved | Tier B coarse path | "(observed)" wording, `confidence: coarse` |
| Governed plane unknown (most sites) | derived from raw irr, `confidence: observed_uncalibrated` | no POA/cell wording |
| Site-list row with no per-site condition available | `unavailable` | `CloudOff`, neutral |

Honesty rules enforced: `null` irradiance never becomes `0`; a measured `0`
irradiance at night is `nighttime`, a measured `0` in daytime is `low_light`/
`overcast_unknown` (not "sunny", not "unavailable" unless truly missing); the word
"rainy" is never emitted.

---

## 5. Affected frontend files

| File | Change |
| --- | --- |
| `src/components/common/WeatherIndicator/WeatherIndicator.tsx` | Generalize (or add sibling `NativeWeatherStatus`) to accept `state` + `label` and render the MUI icon per state + accessible `aria-label`; retain a transitional `imageSrc` path only until decommission, then remove it |
| `…/SiteDetails/tabs/Overview/widgets/ActualProduction/ActualProduction.tsx` | Replace `weatherDescription`/`weatherIconUrl` derivation with `NativeWeatherCondition` (from the performance-context additive block or a `useNativeWeatherCondition` hook); honest tooltip + "unavailable" state |
| `…/CompanyDetails/tabs/Sites/Sites.tsx` | Consume the per-site condition from the site-list payload (or batch endpoint) instead of `weather_description`/`weather_icon_url` |
| `…/my-portfolio/pages/PortfolioPage/components/Sites.tsx` | Same as above |
| `src/api/operations-and-maintenance.ts` | Deprecate `weather_description`/`weather_icon_url`; add the `NativeWeatherCondition` type; update the `weather` field shape |
| `…/WeatherIndicator/__tests__/WeatherIndicator.test.tsx` | Update to state-driven rendering |
| `…/ActualProduction/__tests__/ActualProduction.test.tsx` | Update fixtures to the condition object; add unavailable/stale cases |
| *(new)* `src/hooks/useNativeWeatherCondition.ts` (optional) | Shared fetch/derive hook so widget + lists stay consistent |

---

## 6. Affected backend routes / services (if any)

All additive and read-only; **no** change to `expected_service`, baseline math,
`WeatherResolver` semantics, ingestion, or the scheduler.

| Component | Change |
| --- | --- |
| *(new)* `services/telemetry/native_weather_condition_service.py` | Pure read-only `derive_site_condition(db, site, window)` → `NativeWeatherCondition`. Reuses the **already-fetched** `irradiance_wm2`/`temperature`/`freshness`/`weather_semantics`; **no new DB query** for the single-site path |
| *(new)* `helpers/solar_position.py` | Pure-Python solar zenith + Haurwitz clear-sky GHI (Tier A). No external dependency. Includes `lon_lat_url` parser with safe fallback to Tier B |
| `schema/telemetry_v2.py` | Add an **additive** `observed_condition: NativeWeatherCondition` field to `PerformanceContextResponse` (existing fields unchanged) |
| `services/telemetry/performance_context_service.py` | Populate `observed_condition` by calling the new service with the series it already computes (composition-only, still zero writes) |
| **Site-list path** (lists #3/#4) | Either (a) extend the existing site-list `weather` block (`schema/om_site.py` + the route/CRUD that fills `Site.latest_weather_info`) to emit `NativeWeatherCondition` instead of Weatherstack description/icon, **or** (b) add a small read-only batch endpoint `GET /api/telemetry/v2/sites/weather-conditions?site_ids=…`. Recommendation: (a) to avoid a new round-trip, keeping the list payload shape stable |

No new router file is strictly required if we extend `performance-context` +
the site-list response; the optional batch endpoint is the only net-new route and
only if (b) is chosen.

---

## 7. Migration impact

- **Core design: no migration required.** It reads existing rollups
  (`irradiance_wm2`, `cell_temperature_f`), the site `timezone`, and the existing
  performance-context composition.
- **Optional, deferred, justified-only:** if parsing lat/long from `lon_lat_url`
  proves unreliable in production, add **additive nullable** numeric
  `latitude`/`longitude` columns to `sites` to make Tier A robust. This is the
  *only* conceivable migration, it is non-destructive, and it is **explicitly out
  of scope for this sprint** — recommended as a follow-up *iff* URL parsing is
  shown to fail for real sites. Until then, Tier B is the honest fallback.
- The eventual **drop of `sites_weather`** is part of decommission (§10), not of
  shipping the native indicator.

---

## 8. Testing plan

**Backend (unit, `native_weather_condition_service` + `solar_position`):**
- Night: `irr≈0` + night local hour ⇒ `nighttime` (both tiers).
- Sunny: high `kt` (Tier A) / high `irr` (Tier B) ⇒ `sunny`.
- Partly/cloudy: mid/low `kt` daytime ⇒ `partly_cloudy`/`cloudy`.
- Low-light: low solar elevation (Tier A) / dark daytime (Tier B) ⇒ `low_light`.
- Overcast-unknown: very low daytime `kt` ⇒ `overcast_unknown`, label contains
  "undetermined", **never "rainy"**.
- Unavailable: null irradiance / `no_data` ⇒ `unavailable`; stale ⇒ `coarse` +
  `as_of`.
- Honesty invariants: null never → `0`; a measured `0` is classified by
  time/elevation, not dropped; `plane_governed=false` ⇒ no POA wording.
- `solar_position`: zenith/clear-sky values at known lat/long+timestamps within
  tolerance; `cos(Z) ≤ 0` ⇒ `GHI_cs = 0`.
- `lon_lat_url` parser: valid URL ⇒ lat/long; garbage/empty ⇒ `None` (Tier B).
- Contract: `performance-context` change is purely additive (existing fields and
  values unchanged) — snapshot/regression test.

**Frontend:**
- `WeatherIndicator`/`NativeWeatherStatus`: correct icon + `aria-label` per state;
  `unavailable` renders `CloudOff` + neutral.
- `ActualProduction`: tooltip honesty (observed/uncalibrated wording), unavailable
  + stale states, no POA wording without governance.
- Lists (#3/#4): per-row condition from payload; empty ⇒ unavailable.
- Demo sites: condition derives from demo irradiance without special weather text.

---

## 9. Browser validation plan (read-only, post-implementation)

> In **this** dev environment the native weather/ telemetry tables are largely
> empty (see source audit §10), so expect **`unavailable`** for most sites — that
> is itself a valid validation of the null path.

1. **Site Performance Overview (`ActualProduction`):** open a site with telemetry;
   confirm the icon/label/tooltip match the irradiance series shown in the V2
   Telemetry `PerformanceContextPanel` for the same window; confirm wording is
   "observed/uncalibrated" and never POA unless that site has a governed POA
   mapping.
2. **Day vs night:** view windows spanning local night; confirm `nighttime`
   (irr≈0 + night band) vs daytime states.
3. **Unavailable path:** open a site with no telemetry; confirm "Observed weather
   unavailable" + `CloudOff` (no 0, no fabricated condition).
4. **Stale path:** a site with old-but-present readings shows the derived state +
   "(last seen …)".
5. **Lists:** Company → Sites and My Portfolio → Sites show per-row conditions;
   confirm no broken images and no Weatherstack description leakage.
6. **Governance separation:** a site with a governed POA mapping may show
   "(governed POA)"; an ungoverned site must not.
7. **Parallel-run check:** confirm the Weatherstack path still writes
   `sites_weather` unchanged (dual-run) until decommission begins.

---

## 10. Decommission path for Weatherstack (after replacement ships)

Phased and reversible; physics untouched throughout. Cross-reference
`docs/weather_data_source_audit.md` §15–§16 for the full file list.

1. **Dual-run.** Ship the native `observed_condition`; FE reads native and stops
   reading `weather_description`/`weather_icon_url`. Weatherstack keeps writing
   `sites_weather` (no behavior depends on it anymore). Validate in production.
2. **Stop the source.** Disable the **GCP Cloud Scheduler** job and the
   `fetch_sites_weather` Cloud Function (Terraform in
   `infra/ilios-infra/.../gh-cloudbuild.tf`); remove the
   `weather_provider_access_key` secret from the services tier. (Cancels the paid
   dependency.)
3. **Remove the sink.** Delete `POST /api/internal/sites/weather` +
   `GET /api/internal/sites/locations`, `SiteWeatherCRUD`, the `Site.weather`
   relationship + `latest_weather_info`, the `app/schema/om_site.py` weather
   schemas (`WeatherSchema`, `SiteWeatherSchema`, `CreateSiteWeatherList`, and the
   `latest_weather_info` field), and (migration) the `sites_weather` table. Remove
   the deprecated FE `OMSiteWeather.weather_description`/`weather_icon_url` types
   and any transitional `imageSrc` path.
4. **Verify.** Confirm no remaining references; physics/expected/baseline/
   reconciliation remain byte-identical (they never depended on Weatherstack).

Each phase is independently reversible up to step 3 (the table drop is the only
irreversible action and comes last).

---

## 11. Confirmation: no production code changed

**No production code, schema, migration, API route, scheduler, configuration, or
data was changed in this sprint.** No weather refreshes were triggered, nothing
was deleted, and no Site 4 (or any site/company) record was mutated. The
investigation was read-only (code reading + repository search; the live-DB facts
referenced here come from the companion source audit's read-only `SELECT`s). The
**only** file authored by this sprint is this document,
`docs/native_weather_indicator_replacement_audit.md` — a design deliverable, not
production code.
