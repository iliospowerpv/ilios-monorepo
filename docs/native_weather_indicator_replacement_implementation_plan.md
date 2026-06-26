# Native Weather Indicator Replacement — Implementation Plan

> **Type:** Implementation **planning** — no code is written yet. This document is
> the pre-implementation deliverable requested before building.
> **Date:** 2026-06-26.
> **Approved direction:** replace the paid Weatherstack cosmetic indicator with a
> **native "observed light level"** derived from existing iliOS telemetry /
> performance-context data. **No Weatherstack removal yet. No paid provider. No
> weather-semantics changes.**
> **Upstream:** `docs/native_weather_indicator_replacement_audit.md` (audit +
> design) and `docs/weather_data_source_audit.md` (source-of-truth audit).

---

## 0. Approach in one paragraph

A single read-only service (`native_weather_condition_service.derive_site_condition`)
is the **only** place that maps observed telemetry → an `ObservedCondition`. It is
fed inputs the caller already has (latest non-null irradiance bucket, freshness,
governed semantics flag, site timezone + parsed coordinates) so it adds **no new
DB query** on the single-site path. Two consumers call it:

1. **Single-site widget** (`ActualProduction`) reads a new **additive**
   `observed_condition` field on the V2 `performance-context` response.
2. **Site-card lists** (the two `Sites.tsx`) read the native condition through the
   existing legacy O&M company-sites endpoint, whose `weather` field is
   **content-swapped** from the Weatherstack `latest_weather_info` to the native
   `ObservedCondition` (same field name, new shape).

The Weatherstack pipeline keeps running untouched (dual-run); the FE simply stops
reading its description/icon. Nothing in expected-model, baseline math, the
WeatherResolver, weather declarations, ingestion, or the scheduler is touched.

---

## 1. Affected frontend files

| File | Change | Risk |
| --- | --- | --- |
| `src/components/common/WeatherIndicator/WeatherIndicator.tsx` | Add a state-driven render path: new optional prop `condition?: ObservedCondition` → map `state` to an MUI icon (`WbSunny`/`WbCloudy`/`Cloud`/`Grain`/`WbTwilight`/`DarkMode`/`CloudOff`) + `aria-label` + color. Keep the legacy `imageSrc` prop working during dual-run (do **not** delete it yet). | Low — additive prop; legacy path preserved |
| `…/SiteDetails/tabs/Overview/widgets/ActualProduction/ActualProduction.tsx` | **Keep** its existing `getSiteDashboardProduction(siteId)` query (production / system-size / cumulative) and its `useSiteLatestTelemetry(siteId)` hook **untouched**; **add** a performance-context read (new `useNativeWeatherCondition(siteId)` hook → `ApiClient.telemetryV2.getSitePerformanceContext`) and drive the icon/tooltip from its `observed_condition`. Replace the old `weatherDescription`/`weatherIconUrl` derivation; tooltip = honest basis string; render `unavailable` honestly. | Med — **adds** one query; existing queries unchanged |
| `…/operations-and-maintenance/pages/CompanyDetails/tabs/Sites/Sites.tsx` | `weatherIndicatorCellRenderer` consumes `value` as `ObservedCondition` (not `{weather_description, weather_icon_url}`): render `<WeatherIndicator condition={value} />` + honest tooltip; null → `CloudOff`. AG Grid `field: 'weather'` unchanged. | Low — single cell renderer |
| `…/my-portfolio/pages/PortfolioPage/components/Sites.tsx` | Identical cell-renderer change as above. | Low |
| `src/types/telemetryV2.ts` | Canonical home of `ObservedCondition` + `ObservedTemperature`; add the additive `observed_condition: ObservedCondition \| null` to `PerformanceContextResponse`. | Low — types |
| `src/api/telemetryV2.ts` | `getSitePerformanceContext` now returns the additive `observed_condition`; no signature change. | Low |
| `src/api/operations-and-maintenance.ts` | Import/re-use `ObservedCondition`; change `OMSiteInfo.weather` from `OMSiteWeather \| string \| null` to `ObservedCondition \| null`; mark `OMSiteWeather` (`weather_description`/`weather_icon_url`) `@deprecated` (kept until decommission). | Low — types |
| *(new)* `src/hooks/useNativeWeatherCondition.ts` | Shared hook wrapping `getSitePerformanceContext` and selecting `observed_condition`, so the widget (and any future single-site consumer) stay consistent. | Low |
| `…/WeatherIndicator/__tests__/WeatherIndicator.test.tsx` | Re-point to state-driven rendering; cover each `state` + `unavailable`. | Low |
| `…/ActualProduction/__tests__/ActualProduction.test.tsx` | Update fixtures from `{weather_description,…}` to `observed_condition`; add unavailable/stale cases. | Low |

No other production FE file reads `weather_description`/`weather_icon_url`/
`WeatherIndicator` (verified by repo search).

---

## 2. Affected backend files / routes

All additive and read-only. **No** change to `expected_service`, baseline math,
`weather_resolver`, `weather_device_mappings`/declarations, ingestion, or the
scheduler.

| File | Change |
| --- | --- |
| *(new)* `app/services/telemetry/native_weather_condition_service.py` | Pure read-only `derive_site_condition(...) -> ObservedCondition` (the single source of truth). Inputs are passed in (no internal CRUD calls) so it stays query-free and unit-testable. |
| *(new)* `app/helpers/solar_position.py` | Pure-Python solar zenith + Haurwitz clear-sky GHI (Tier A) + a tolerant `parse_lon_lat(lon_lat_url) -> Optional[tuple[float,float]]`. No external dependency, no network. |
| `app/schema/telemetry_v2.py` | Add `ObservedCondition` + `ObservedTemperature` models; add an **additive, nullable** `observed_condition: Optional[ObservedCondition] = None` to `PerformanceContextResponse`. |
| `app/services/telemetry/performance_context_service.py` | After the series is built, compute `observed_condition` from the **already-fetched** latest non-null `irradiance_wm2` bucket + `temperature` + `telemetry_quality.freshness_state` + the governed `weather_semantics` flag (composition-only, still zero writes, still 0-vs-null). |
| `app/routers/telemetry/v2.py` | No new route needed — `GET /api/telemetry/v2/sites/{site_id}/performance-context` (`get_site_performance_context`) now returns the additive field. |
| `app/schema/om_site.py` | The list-item schema serializes `latest_weather_info` under **`serialization_alias="weather"`**, and `Site.latest_weather_info` is a **read-only property over the ordered `weather` relationship** — so the implementation must **NOT** assign/mutate `site.weather`. Build a **transient DTO** (dict, or a new transient response model) whose `latest_weather_info`/`weather` carries the `ObservedCondition`. Widen the field type to `Optional[ObservedCondition \| WeatherSchema \| str]` during dual-run. Weatherstack `WeatherSchema`/`SiteWeatherSchema`/`CreateSiteWeatherList` **left intact** (decommission only). |
| `app/routers/operations_and_maintenance/companies.py` (`get_company_sites` → `extend_company_sites_with_energy_attributes`) | This endpoint returns ORM `Site` rows enriched by **batched** energy helpers (latest power / baseline / expected); it does **not** currently read irradiance/freshness. Add a **batched** "latest-irradiance + freshness **by site_id**" helper (a single query for all sites, mirroring the existing energy-attribute batching — **NO N+1, NO per-site performance-context build**), call `derive_site_condition` per row, and serialize the result into the `weather` alias via the transient DTO above. |
| `app/routers/operations_and_maintenance/sites.py` (site production section feeding `ActualProduction`) | **No change required** in the recommended approach — the widget reads `observed_condition` from performance-context, so this legacy endpoint stays as-is. (Only touch it if a later decision routes the widget back through it.) |

> **Note on the ingestion-vs-display irradiance plane:** the read service never
> asserts the plane. It labels `plane_governed` from the governed
> `weather_semantics` only; it never calls the WeatherResolver to drive the icon.

---

## 3. Exact `observed_condition` contract

### 3.1 Backend (Pydantic, `app/schema/telemetry_v2.py`)
```python
class ObservedTemperature(BaseModel):
    value: float
    unit: Literal["F", "C"]
    type: Optional[str] = None          # governed temperature_type ONLY; else None

class ObservedCondition(BaseModel):
    state: Literal[
        "sunny", "partly_cloudy", "cloudy", "overcast_unknown",
        "low_light", "nighttime", "unavailable",
    ]
    label: str                          # honest human caption (see §4)
    light_level: Optional[Literal["strong", "moderate", "low", "dark"]] = None
    observed_irradiance_wm2: Optional[float] = None   # null = unavailable, never 0-as-fallback
    plane_governed: bool = False        # True ONLY if governed POA; gate for any "POA" wording
    temperature: Optional[ObservedTemperature] = None
    confidence: Literal[
        "observed_calibrated",          # plane is governed (NOT meteorological calibration)
        "observed_uncalibrated",        # Tier A, ungoverned plane
        "coarse",                       # Tier B or stale
        "unavailable",
    ]
    tier: Literal["A", "B"]             # which path produced it (diagnostic/telemetry)
    as_of_utc: Optional[datetime] = None
    as_of_site_local: Optional[datetime] = None
    data_quality: Literal["fresh", "stale", "no_data"]
```
The "unavailable" default factory:
`ObservedCondition(state="unavailable", label="Observed weather unavailable",
confidence="unavailable", tier=<A|B>, data_quality=<from freshness>)`.

### 3.2 Frontend (TS — canonical home `src/types/telemetryV2.ts`; re-used by `src/api/operations-and-maintenance.ts`)
```ts
export interface ObservedTemperature { value: number; unit: 'F' | 'C'; type: string | null; }
export interface ObservedCondition {
  state: 'sunny' | 'partly_cloudy' | 'cloudy' | 'overcast_unknown'
       | 'low_light' | 'nighttime' | 'unavailable';
  label: string;
  light_level: 'strong' | 'moderate' | 'low' | 'dark' | null;
  observed_irradiance_wm2: number | null;
  plane_governed: boolean;
  temperature: ObservedTemperature | null;
  confidence: 'observed_calibrated' | 'observed_uncalibrated' | 'coarse' | 'unavailable';
  tier: 'A' | 'B';
  as_of_utc: string | null;
  as_of_site_local: string | null;
  data_quality: 'fresh' | 'stale' | 'no_data';
}
```

---

## 4. Derivation algorithm

**Inputs (per site):** `irr` = latest **non-null** `irradiance_wm2` in the window
(+ its `bucket_start_utc`/`_site_local`); `freshness` ∈ {fresh,stale,no_data};
`plane_governed` = governed POA flag from `weather_semantics`; `latlon` =
`parse_lon_lat(site.lon_lat_url)` or None; optional latest `temperature` + its
governed `type`.

**Step 1 — Availability gate (runs first):**
- `freshness == no_data` OR `irr is None` ⇒ `state=unavailable`,
  `data_quality=freshness`, `confidence=unavailable`. **Stop.**

**Step 2 — Tier A (only if `latlon` resolved):** compute solar zenith `Z` for
`(lat, lon, bucket_start_utc)`; clear-sky GHI `GHI_cs = 1098·cosZ·exp(-0.057/cosZ)`
for `cosZ>0` else 0; `kt = irr / GHI_cs` (guard `GHI_cs>0`).

| Rule | state | label |
| --- | --- | --- |
| `cosZ ≤ 0` | `nighttime` | "Nighttime" |
| sun up, elevation `< ~5°` | `low_light` | "Low light (dawn/dusk)" |
| `kt ≥ 0.75` | `sunny` | "Sunny / clear (observed)" |
| `0.40 ≤ kt < 0.75` | `partly_cloudy` | "Partly cloudy (observed)" |
| `0.15 ≤ kt < 0.40` | `cloudy` | "Cloudy / overcast (observed)" |
| `kt < 0.15`, sun well up | `overcast_unknown` | "Overcast / precipitation (undetermined)" |

`tier="A"`; `confidence = observed_calibrated if plane_governed else observed_uncalibrated`.

**Step 2′ — Tier B (no `latlon`):** coarse observed-light bands; night via local time.

| Rule | state | label |
| --- | --- | --- |
| `irr ≤ 5` AND local hour ∈ night band (20:00–05:00) | `nighttime` | "Nighttime" |
| `irr ≤ 5` AND daytime hour | `low_light` | "Low light / dark (undetermined)" |
| `irr ≥ 600` | `sunny` | "Strong sunlight (observed)" |
| `150 ≤ irr < 600` | `partly_cloudy` | "Moderate light (observed)" |
| `5 < irr < 150` daytime | `cloudy` | "Low light / overcast (observed)" |

`tier="B"`; `confidence = coarse`.

**Step 3 — Staleness overlay (both tiers):** if `freshness == stale`, keep the
derived `state` but set `confidence=coarse`, `data_quality=stale`, and append
"(last seen {as_of_site_local})" to `label`.

**Step 4 — Light level + temperature:** set `light_level` from `irr`
(strong ≥600 / moderate 150–600 / low 5–150 / dark ≤5). Attach `temperature` only
if a temp reading exists; set `temperature.type` **only** when governed, else null.

**Step 5 — POA guard:** any "POA"/"cell" wording is allowed **iff**
`plane_governed` is true; otherwise the label/tooltip stays "observed
(uncalibrated)". The string "rain"/"rainy" is **never** emitted — the wettest
honest state is `overcast_unknown` → "…precipitation (undetermined)".

Thresholds (`0.75/0.40/0.15`, `600/150/5`, night band, `5°`) live as named module
constants for tuning and test pinning.

---

## 5. Fallback / null behavior

| Situation | Result | Render |
| --- | --- | --- |
| No non-null irradiance in window | `state=unavailable`, `data_quality` from freshness | `CloudOff` + "Observed weather unavailable" |
| `freshness == no_data` / not configured | `state=unavailable` | same |
| Stale but last reading exists | derived state, `confidence=coarse` | icon + "(last seen …)" |
| Daytime irr ≈ 0 (outage vs heavy weather — indistinguishable) | `low_light` (B) / `overcast_unknown` (A) | "undetermined" wording, **never "rainy"** |
| `latlon` unresolved | Tier B, `confidence=coarse` | "(observed)" wording |
| Plane ungoverned (most sites) | `observed_uncalibrated` | no POA/cell wording |
| List row with no condition computable | `null` | `CloudOff`, neutral tooltip |

Invariants enforced in code + tests: `observed_irradiance_wm2` null never becomes
`0`; a **measured** `0` is classified by time/elevation (night vs low-light), never
dropped and never "sunny"; `unavailable` is the only no-data outcome.

---

## 6. Site / list data strategy

- **Single source of truth:** `derive_site_condition` — both consumers call it so
  the widget and the list agree by construction.
- **Single-site widget (`ActualProduction`):** **keep** its existing
  `getSiteDashboardProduction(siteId)` query and `useSiteLatestTelemetry(siteId)`
  hook **untouched**; **add** a `useNativeWeatherCondition(siteId)` hook wrapping
  `ApiClient.telemetryV2.getSitePerformanceContext` and read `observed_condition`
  from it. This is an **added** query, not a redirect. *Rationale:* V2 owns the
  derivation and the legacy O&M production endpoint stays free of new telemetry math.
- **Lists (both `Sites.tsx`):** the company sites-list endpoint
  (`routers/operations_and_maintenance/companies.py` → `get_company_sites` →
  `extend_company_sites_with_energy_attributes`) enriches ORM `Site` rows via
  **batched** energy helpers — it does **not** currently read irradiance/freshness.
  Add a **batched** "latest-irradiance + freshness **by site_id**" helper (a single
  query for all sites, same batching pattern as the energy attributes — **NOT N+1,
  NOT a per-site performance-context build**), call `derive_site_condition` per row,
  and serialize the result into the existing `weather` field via a transient DTO
  (the `latest_weather_info`→`weather` alias path; **do not mutate `site.weather`**).
  AG Grid `field: 'weather'` + the cell renderer keep their shape — only the value
  type changes. *Rationale:* one extra **batched** query, no round-trip, no N
  performance-context builds.
- **Batch endpoint (rejected for now):** a dedicated
  `GET …/sites/weather-conditions?site_ids=…` is simpler to reason about but adds
  a round-trip and duplicates the list's per-site loop; revisit only if the
  list-endpoint coupling proves awkward.
- **Demo sites:** condition derives from demo irradiance exactly like real sites;
  the `DEMO_` icon special-case is removed with the image path (no special weather
  text — honesty preserved).

---

## 7. Migration impact

- **None for the core.** Uses existing rollups (`irradiance_wm2`,
  `cell_temperature_f`), `Site.timezone`, `Site.lon_lat_url`, and the existing
  performance-context composition.
- **Optional, deferred, justified-only:** additive **nullable** numeric
  `latitude`/`longitude` on `sites` *iff* `parse_lon_lat(lon_lat_url)` proves
  unreliable on real data — this would upgrade more sites from Tier B to Tier A.
  Non-destructive; **explicitly out of scope** for this build. Until then Tier B
  is the honest fallback. (No other migration is contemplated; `sites_weather` is
  dropped only at decommission — §10.)

---

## 8. Tests

**Backend — `native_weather_condition_service` + `solar_position` (new test files):**
- Tier A: night (`cosZ≤0`), dawn/dusk (`<5°`), sunny (`kt≥0.75`), partly
  (`0.4≤kt<0.75`), cloudy (`0.15≤kt<0.4`), overcast_unknown (`kt<0.15`) — label
  contains "undetermined", **never "rainy"**.
- Tier B: night-band dark, daytime dark, strong/moderate/low bands.
- Availability: `irr None` ⇒ unavailable; `no_data` ⇒ unavailable; stale ⇒
  derived + `coarse` + "(last seen …)".
- Honesty invariants: null ≠ 0; measured `0` classified, not dropped;
  `plane_governed=False` ⇒ no "POA" substring; temperature `type` null unless
  governed.
- `solar_position`: zenith/clear-sky within tolerance at known lat/lon/timestamps;
  `cosZ≤0 ⇒ GHI_cs=0`. `parse_lon_lat`: valid URL ⇒ coords; garbage/empty ⇒ None.
- **Contract regression:** a `performance-context` snapshot test proving the change
  is purely additive (all pre-existing fields/values byte-identical;
  `observed_condition` is the only new key).

**Frontend:**
- `WeatherIndicator`: correct icon + `aria-label` per `state`; `unavailable` ⇒
  `CloudOff`; legacy `imageSrc` path still renders (dual-run).
- `ActualProduction`: tooltip basis wording (observed/uncalibrated), unavailable +
  stale states, no "POA" without governance, no "rainy" ever.
- Both `Sites.tsx` cell renderers: render condition from `OMSiteInfo.weather`;
  null ⇒ `CloudOff`.

---

## 9. Browser validation (post-build, read-only)

> In this dev environment native telemetry is largely empty, so expect
> `unavailable` for most sites — that itself validates the null path.

1. **Overview `ActualProduction`:** icon/label/tooltip match the irradiance series
   in the V2 Telemetry `PerformanceContextPanel` for the same window; wording is
   "observed/uncalibrated"; "POA" only on a governed-POA site.
2. **Day vs night:** windows spanning local night show `nighttime`.
3. **Unavailable:** a no-telemetry site shows "Observed weather unavailable" +
   `CloudOff` (no 0, no fabricated condition).
4. **Stale:** an old-readings site shows derived state + "(last seen …)".
5. **Lists:** Company → Sites and My Portfolio → Sites show per-row conditions; no
   broken images, no Weatherstack description leakage.
6. **Dual-run:** confirm Weatherstack still writes `sites_weather` (unchanged) and
   that physics/expected/baseline outputs are byte-identical before vs after.

---

## 10. Weatherstack dual-run / decommission boundary

**This build does ONLY the dual-run half. The decommission half is explicitly NOT
in this build.**

In scope now (dual-run):
- Add the native derivation + `observed_condition`; switch the FE (widget + lists)
  to read native; stop the FE reading `weather_description`/`weather_icon_url`.
- Weatherstack pipeline (GCP scheduler + `fetch_sites_weather` function + the
  `weather_provider_access_key` secret + `POST /api/internal/sites/weather` +
  `SiteWeatherCRUD` + `sites_weather` + `Site.latest_weather_info`) **stays fully
  intact and running**; the FE just ignores its output.
- FE `OMSiteWeather` types marked `@deprecated` but **kept**; `WeatherIndicator`'s
  `imageSrc` path **kept**.

The boundary line (NOT crossed in this build, tracked for a later sprint):
- Stop the GCP scheduler/function + remove the secret.
- Delete `/api/internal/sites/weather` + `/api/internal/sites/locations`,
  `SiteWeatherCRUD`, `Site.weather`/`latest_weather_info`, the `om_site.py`
  Weatherstack schemas (`WeatherSchema`/`SiteWeatherSchema`/`CreateSiteWeatherList`),
  the deprecated FE types, and the `imageSrc` path; **migration** to drop
  `sites_weather`.

Rollback: until the FE swap is approved, the legacy `imageSrc`/description path is
still present, so reverting is a FE-only change.

---

## Constraint-compliance matrix

| Hard constraint | How this plan honors it |
| --- | --- |
| No expected-model changes | `expected_service` untouched; only reads its already-composed outputs |
| No baseline math changes | No baseline code touched; baseline values read verbatim |
| No WS.5 | Not referenced or modified |
| No weather-declaration changes | `weather_device_mappings`/declarations read-only; never written |
| No provider integration / no paid API | Pure-Python solar math; zero external calls or secrets |
| No migrations unless justified | Core needs none; optional lat/long column deferred & flagged |
| Never label raw irradiance as POA unless governed | `plane_governed` gate; "POA" wording only when governed |
| Never emit "rainy" | Wettest state is `overcast_unknown` → "precipitation (undetermined)" |
| Null ≠ 0 | `observed_irradiance_wm2` null never coerced to 0; measured 0 classified by time |
| Unavailable renders honestly | `state=unavailable` → `CloudOff` + "Observed weather unavailable" |

---

## Ordered implementation task breakdown (for when approved)

1. **BE-1** `helpers/solar_position.py` (+ tests) — zenith, clear-sky GHI,
   `parse_lon_lat`. *(no deps)*
2. **BE-2** `ObservedCondition`/`ObservedTemperature` schemas in `telemetry_v2.py`.
   *(no deps)*
3. **BE-3** `native_weather_condition_service.derive_site_condition` (+ tests).
   *(deps: BE-1, BE-2)*
4. **BE-4** Add additive `observed_condition` to `PerformanceContextResponse` +
   populate in `performance_context_service` (+ contract regression test).
   *(deps: BE-3)*
5. **BE-5** Add a **batched** latest-irradiance+freshness-**by-site** helper; call
   `derive_site_condition` per row in the company sites-list endpoint
   (`operations_and_maintenance/companies.py`); serialize into the `weather` alias
   via a transient DTO (**no `site.weather` mutation**); widen `om_site.py` type.
   *(deps: BE-3)*
6. **FE-1** `ObservedCondition`/`ObservedTemperature` TS types in
   `types/telemetryV2.ts` + additive `observed_condition` on
   `PerformanceContextResponse` (consumed by `api/telemetryV2.ts`
   `getSitePerformanceContext`); retype `OMSiteInfo.weather` in
   `api/operations-and-maintenance.ts`; deprecate `OMSiteWeather`.
   *(deps: BE-2/BE-4 shape)*
7. **FE-2** `WeatherIndicator` state-driven render (keep `imageSrc`). *(deps: FE-1)*
8. **FE-3** `useNativeWeatherCondition(siteId)` hook (wraps
   `getSitePerformanceContext`); `ActualProduction` **adds** that read and swaps the
   icon/tooltip while **keeping** its existing production + latest-telemetry queries.
   *(deps: BE-4, FE-1, FE-2)*
9. **FE-4** Both `Sites.tsx` cell renderers. *(deps: BE-5, FE-1, FE-2)*
10. **FE-5/BE-6** Update FE + BE tests; run browser validation (§9).
    *(deps: all)*

Dependencies are intra-sprint (single environment); BE-1/BE-2 and the FE typing
can start in parallel, everything else follows the chain above.
