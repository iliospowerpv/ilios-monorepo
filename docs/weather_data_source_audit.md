# Weather Data Source & Ingestion Audit

> **Type:** Audit / design sprint — **READ-ONLY**.
> **Scope:** Determine exactly where iliOS obtains all weather data, whether
> Weatherstack is still used anywhere, and trace the complete ingestion pipeline
> from external provider to UI.
> **Date:** 2026-06-26.
> **Constraint compliance:** No production code, migrations, schema, config, API,
> scheduler, or data was changed. No weather refreshes were triggered. No Site 4
> mutations. The only artifact produced is this document. (See §17 and §20.)

---

## 1. Executive summary

iliOS has **two completely disjoint weather systems** that do not share code,
storage, or credentials:

1. **Legacy "cosmetic" weather (Weatherstack).** A separate GCP cloud-function
   tier (`backend/ilios-services`, *not* the main `backend/ilios-server` app)
   calls the **Weatherstack** API hourly and writes a short **weather
   description + icon URL** into the Postgres `sites_weather` table. This is the
   **only** live external weather provider in the entire codebase. It feeds a few
   purely decorative UI elements (a tooltip + a small weather icon on site
   cards). **It feeds no physics, no expected generation, no baseline, and no
   reconciliation math.**

2. **Native weather provenance domain (W0/W1/W2).** An in-platform,
   PostgreSQL-only weather architecture (`weather_sources`,
   `weather_source_profiles`, `weather_observation_batches`,
   `weather_observations`, `weather_source_approvals`,
   `weather_device_mappings`, `expected_weather_provenance`). It has **no
   external provider, no API key, no secret, and no BigQuery/Firestore
   dependency.** It is the source of weather *for calculations* (expected
   generation, weather-adjusted baseline, O&M charts, degradation). Weather
   values here come from either **DAS telemetry** (W1, the live default) or
   **manually imported historical weather files** (W2). There is **no scheduler**
   for this domain — ingestion is operator-triggered only.

**Headline answers:**

| Question | Answer |
| --- | --- |
| Is Weatherstack still used? | **Yes** — but only in the legacy `backend/ilios-services` cloud-function tier, for cosmetic description/icon. Not in `backend/ilios-server`. |
| Are Weatherstack credentials still required? | **Yes**, for that legacy tier only (`weather_provider_access_key`). The main app and this Replit environment do **not** hold or use it. |
| Can Weatherstack be safely removed? | **Yes, from a data-integrity standpoint** — it drives zero calculations. Removal only drops a cosmetic site-card weather description/icon, so it needs product sign-off, not engineering risk acceptance. (See §15.) |
| Any other live external provider (OpenWeather, NOAA, NREL, Solcast, Tomorrow.io, Visual Crossing, Meteostat)? | **No.** None are referenced anywhere in the code (only in the audit prompt). NREL/PVWatts/PVGIS hits are PVsyst document-parsing prompts, not weather API clients. |

**Live state in this dev environment (read-only):** the cosmetic `sites_weather`
table holds **2 stale rows** (sites 18 & 19, last updated **2026-04-16**, ~10
weeks ago), and the **entire native weather domain is empty** (0 observations, 0
sources, 0 profiles, 0 device mappings). So in dev, physics weather is served
exclusively by DAS telemetry (W1), never W2, and is **never semantics-verified**
(no device mappings declared). (See §10.)

---

## 2. Current weather architecture

```
                         ┌──────────────────────────────────────────────────────┐
                         │  SYSTEM A — LEGACY COSMETIC WEATHER (Weatherstack)     │
                         │  Tier: backend/ilios-services  (separate GCP repo)     │
                         └──────────────────────────────────────────────────────┘
  Weatherstack API                Cloud Function (gen2, py312)        Main app (ilios-server)
  api.weatherstack.com/current ─▶ fetch_sites_weather ─────────────▶ POST /internal/sites/weather
        ▲  (hourly cron)          SitesManager.process_sites_weather   (api_key protected)
        │                         reads weather_descriptions[0]              │
  GCP Cloud Scheduler             + weather_icons[0] only                    ▼
  "0 * * * *"                                                        SiteWeatherCRUD.create_items
  (gh-cloudbuild.tf)                                                         │
                                                                            ▼
                                                                 Postgres  sites_weather
                                                                 (weather_description, weather_icon_url)
                                                                            │
                                                                            ▼
                                                  FE (cosmetic): ActualProduction widget,
                                                  CompanyDetails > Sites, Portfolio > Sites
                                                  (tooltip + WeatherIndicator icon)


                         ┌──────────────────────────────────────────────────────┐
                         │  SYSTEM B — NATIVE WEATHER PROVENANCE (W0/W1/W2)       │
                         │  Tier: backend/ilios-server  (no external provider)    │
                         └──────────────────────────────────────────────────────┘

  Manual file import                                          DAS telemetry (live default, W1)
  POST /api/weather/sites/{id}/historical-import              telemetry_site_interval_rollups
        │                                                             │
        ▼                                                             │
  HistoricalWeatherImportService.run_historical_import                │
  (idempotent on dedupe_key, ON CONFLICT DO NOTHING)                  │
        ▼                                                             │
  weather_observation_batches + weather_observations  (W2)            │
        │                                                             │
        └──────────────┬──────────────────────────────────────────--┘
                       ▼
            WeatherResolver.resolve_window
            (W2 if an ACTIVE historical profile exists, else W1 DAS)
            semantics_verified ONLY if a WeatherDeviceMapping declares
            poa irradiance + cell/module/modeled_cell temperature
                       │
                       ▼
            expected_service (_load_bucket_inputs) ─▶ expected generation
                       │                            ─▶ weather-adjusted baseline validation
                       │                            ─▶ O&M performance context / charts
                       │                            ─▶ degradation (age_factor)
                       ▼
            FE: PerformanceContextPanel, Telemetry tab weather semantics panels
```

The two systems share **only** the word "weather" and the `Site` entity. They
have separate tables, separate code, separate (or zero) credentials, and serve
separate purposes (cosmetic display vs. physics input).

---

## 3. Active providers

| Provider | Status | Where | Purpose | API key? | Paid? |
| --- | --- | --- | --- | --- | --- |
| **Weatherstack** | **ACTIVE (legacy tier only)** | `backend/ilios-services/common/settings.py`, `services/fetch_sites_weather/` | Cosmetic current-conditions **description + icon** for site cards | **Yes** — `weather_provider_access_key` | **Yes** (Weatherstack is a paid SaaS; a free tier exists with strict limits) |
| **DAS telemetry (in-platform, "provider")** | **ACTIVE** | `telemetry_site_interval_rollups` via `WeatherResolver` (W1) | Physics weather inputs (POA irradiance, cell temp) for expected/baseline | No (internal) | No |
| **Manual historical weather import (in-platform)** | **ACTIVE (operator-triggered)** | `historical_weather_import_service` → `weather_observations` (W2) | Historical weather for replay/expected when an active historical profile exists | No | No |

There is **no live external weather *API* client other than Weatherstack.**

---

## 4. Legacy / dead / not-integrated providers

| Provider | Status | Evidence |
| --- | --- | --- |
| **OpenWeather** | **Not integrated** | Zero references in code (only in the audit prompt). |
| **NOAA** | **Not integrated** | Zero references in code (only in the audit prompt). |
| **Solcast** | **Not integrated** | Zero references in code (only in the audit prompt). |
| **Tomorrow.io** | **Not integrated** | Zero references in code (only in the audit prompt). |
| **Visual Crossing** | **Not integrated** | Zero references in code (only in the audit prompt). |
| **Meteostat** | **Not integrated** | Zero references in code (only in the audit prompt). |
| **NREL / PVWatts / PVGIS** | **Not a weather provider here** | ~73 hits, but all in PVsyst/EPC **document-parsing** prompt CSVs (`docai/`, `backend/ilios-DocAI/`), docs, one FE `UploadButton`, and a `declaration_service.py` comment. None are live weather API calls. |
| **`provider_pull` ingestion path** | **Defined, not implemented** | `WeatherObservationBatchKind.provider_pull` and provider-type enums (`external_modeled_provider`, `das_provider_stream`) exist in `models/weather.py` as **forward placeholders**; `run_historical_import` only implements `file_import` / `manual`. No provider client code exists. |

**Weatherstack itself is "legacy" in spirit** (it predates the native domain and
serves only cosmetic data) but is still **deployed and wired**, so it is
classified as Active-but-peripheral in §3 rather than dead.

---

## 5. Complete ingestion pipeline

### System A — Weatherstack (cosmetic)

| Stage | Component | File |
| --- | --- | --- |
| External API | `GET https://api.weatherstack.com/current?access_key=…&query={location}` | `backend/ilios-services/common/settings.py` (`current_weather_api_url`, `weather_provider_access_key`) |
| Scheduler | **GCP Cloud Scheduler** cron `0 * * * *` (hourly) | `infra/ilios-infra/ilios-infra/template/gh-cloudbuild.tf` (~L187–207) |
| Compute | **GCP Cloud Function (gen2, Python 3.12)** `fetch_sites_weather`; `SitesManager.process_sites_weather` / `update_sites_weather` reads `weather_descriptions[0]` + `weather_icons[0]` only (no temperature/irradiance) | `backend/ilios-services/services/fetch_sites_weather/sites_manager.py`; deploy `…/fetch_sites_weather/cloudbuild.yaml` |
| Site list source | `GET {base_platform_api_url}/internal/sites/locations` → mounted at **`/api/internal/sites/locations`** | `backend/ilios-server/app/routers/internal/sites.py` → `SiteCRUD.get_sites_location` |
| Write-back API | `POST {base_platform_api_url}/internal/sites/weather` → mounted at **`/api/internal/sites/weather`** (auth: `api_key_check`) | `backend/ilios-server/app/routers/internal/sites.py` → `bulk_create_sites_weather` |
| CRUD | `SiteWeatherCRUD.create_items` | `backend/ilios-server/app/crud/site_weather.py` |
| DB table | `sites_weather` (`weather_description`, `weather_icon_url`) | `backend/ilios-server/app/models/site.py` (class `SiteWeather`, L87–99) |
| Frontend | tooltip + icon | `ActualProduction.tsx`, `CompanyDetails/.../Sites.tsx`, `PortfolioPage/.../Sites.tsx`, `WeatherIndicator` |

### System B — Native weather (physics)

| Stage | Component | File |
| --- | --- | --- |
| Source (W1) | DAS telemetry interval rollups | `telemetry_site_interval_rollups` (read via the telemetry rollup CRUD) |
| Source (W2) | Manually imported historical weather | `weather_observations` / `weather_observation_batches` |
| Ingestion (W2) | `preview_import` / `run_historical_import` — idempotent on `dedupe_key` (`INSERT … ON CONFLICT DO NOTHING`) | `backend/ilios-server/app/services/weather/historical_weather_import_service.py` |
| Scheduler | **None** — operator-triggered via API only | n/a |
| Resolver | `WeatherResolver.resolve_window` — W2 if an ACTIVE historical profile exists, else W1 DAS; `semantics_verified` only when a `WeatherDeviceMapping` declares `poa` + `cell/module/modeled_cell` | `backend/ilios-server/app/services/weather/weather_resolver.py` |
| Consumers | expected generation, baseline validation, O&M charts, degradation | `expected_service.py`, `baseline_physics_validation.py`, `performance_context_service.py` |
| API | `/api/weather/*` (13 endpoints) + `/api/telemetry/v2/sites/{id}/performance-context` | `routers/weather.py`, `routers/telemetry/v2.py` |
| Frontend | semantics/declaration panels + performance chart | `WeatherSemanticsPanel.tsx`, `WeatherDeclareDialog.tsx`, `WeatherDeclarationHistoryDialog.tsx`, `PerformanceContextPanel.tsx` |

---

## 6. Database tables

| Table | System | ORM model / file | Purpose | Update semantics |
| --- | --- | --- | --- | --- |
| `sites_weather` | A (cosmetic) | `SiteWeather` — `app/models/site.py` L87–99 | Weatherstack description + icon URL per site | **Appended** (bulk insert via `SiteWeatherCRUD.create_items`, not upsert); the UI reads the latest row via `Site.latest_weather_info` (relationship ordered by `updated_at` desc) |
| `weather_sources` | B | `app/models/weather.py` L256 | Identity/taxonomy of a weather producer (measured vs. modeled); **no secrets** | Append; identity rows |
| `weather_source_profiles` | B | `app/models/weather.py` L311 | Effective-dated, role-tagged (`live/historical/design/fallback`) source policy with approval lifecycle (`draft→…→active→superseded/rejected`); **versioned by new row, never mutated, no auto-activation; overlapping actives allowed via `priority`** | Insert-new-version |
| `weather_observation_batches` | B | `app/models/weather.py` L374 | Immutable provenance record of an import/pull (`file_import/provider_pull/manual/telemetry_backfill`) | Immutable |
| `weather_observations` | B | `app/models/weather.py` L435 | Imported/modeled/manual weather values (NOT a replacement for `telemetry_readings`) | Append/idempotent on `dedupe_key` |
| `weather_source_approvals` | B | `app/models/weather.py` L509 | Append-only approval/audit ledger | Append-only |
| `weather_device_mappings` | B | `app/models/weather.py` L552 | Governed **measurement semantics** declaration (irradiance plane / temperature type / calibration), default `unknown`, never guessed | Governed draft→active→superseded (immutable fingerprint) |
| `expected_weather_provenance` | B | `app/models/weather.py` L696 | **Forward placeholder** — snapshot of which source drove an expected calc | **Never written by any runtime** (only test code instantiates the model; all production references are "NEVER writes" docstrings) |

**Named enums** (`app/models/weather.py`): `WeatherSourceType`,
`WeatherSourceProfileRole`, `WeatherSourceProfileStatus`,
`WeatherObservationBatchKind`, `WeatherIrradiancePlane` (`poa/ghi/dni/dhi/unknown`
— only `poa` is physics-usable; no transposition model), `WeatherTemperatureType`
(`cell/module/ambient/modeled_cell/unknown` — `ambient` is never converted to
cell), plus confidence/calibration enums.

**Migrations:** `c21be722f5cc_define_site_weather_table.py` (legacy
`sites_weather`); `ff32_weather_provenance_foundation.py` (W0 tables);
`ff36_weather_semantics_governed_declaration.py`;
`ff37_weather_declaration_single_active.py`.

---

## 7. Backend services

### System A
- `backend/ilios-services/services/fetch_sites_weather/` — Cloud Function;
  `SitesManager` (`sites_manager.py`) orchestrates fetch + write-back.
- `backend/ilios-services/common/settings.py` — Weatherstack URL + access key,
  internal `api_key`, `base_platform_api_url`; loaded from
  `/etc/secrets/app_values_creds.yaml`.

### System B (`backend/ilios-server/app/services/weather/`)
- `weather_resolver.py` — `WeatherResolver.resolve_window` (read-only; the single
  weather seam into physics). **No writes — not even to `expected_weather_provenance`.**
- `historical_weather_import_service.py` — `preview_import`, `run_historical_import`
  (the only path that inserts `weather_observations`).
- `weather_profile_service.py` — profile create + lifecycle actions.
- `declaration_service.py` / `declaration_policy.py` — governed device-mapping
  semantics (create / activate / re-review).
- `weather_readiness_service.py` — `compute_weather_readiness` (read-only window
  coverage check).
- `semantics_reconciliation_service.py` — read-only semantics reconciliation view.
- `upstream_change_detector.py` / `upstream_fingerprint.py` — detect upstream
  device/source changes that should force re-review.
- `bucketing.py` — interval bucketing helpers.
- CRUD: `app/crud/weather.py` (`WeatherSourceCRUD`, `WeatherSourceProfileCRUD`,
  `WeatherObservationBatchCRUD`, `WeatherObservationCRUD`,
  `WeatherSourceApprovalCRUD`, `WeatherDeviceMappingCRUD`).
- Guard: `app/db/weather_declaration_guard.py` (governed-update enforcement).

---

## 8. Scheduler / jobs

| Job | System | Cadence | Trigger | Notes |
| --- | --- | --- | --- | --- |
| `fetch_sites_weather` | A | **Hourly** (`0 * * * *`) | **GCP Cloud Scheduler** → Cloud Function | Defined in `infra/ilios-infra/ilios-infra/template/gh-cloudbuild.tf`. Runs **only in GCP**, not in this Replit dev environment. |
| Native weather ingestion | B | **None** | — | **No scheduler/cron/queue worker.** Historical import is **manual**, via `POST /api/weather/sites/{id}/historical-import`. |

The main app's only in-process scheduler is the **telemetry scheduler**
(`TelemetrySchedulerRunner`, started from the FastAPI `lifespan` in `app/main.py`,
gated behind `telemetry_scheduler_enabled`). It is **unrelated to weather** and
does **not** ingest weather. There is **no retry/backfill job specific to
weather**; the native importer's idempotency (`dedupe_key`) makes re-importing a
window a safe no-op, which is how a manual backfill is performed.

---

## 9. API routes

### Native weather domain — `/api/weather` (`routers/weather.py`, 13 endpoints)
- `POST /sites/{site_id}/historical-import/preview`
- `POST /sites/{site_id}/historical-import`
- `GET  /sites/{site_id}/historical-readiness`
- `POST /sites/{site_id}/historical-profiles`
- `POST /sites/{site_id}/historical-profiles/{profile_id}/actions`
- `GET  /sites/{site_id}/device-mappings`
- `POST /sites/{site_id}/device-mappings`
- `POST /sites/{site_id}/device-mappings/{mapping_id}/activate`
- `POST /sites/{site_id}/device-mappings/{mapping_id}/re-review`
- `GET  /sites/{site_id}/devices/{device_id}/device-mappings`
- `GET  /sites/{site_id}/device-mappings/upstream-changes`
- `POST /sites/{site_id}/device-mappings/re-evaluate`
- `GET  /sites/{site_id}/semantics-reconciliation`

Authorization: writes require `telemetry_admin_required` + site-admin +
company-visibility; reads require site authorization. **No BigQuery/Firestore/
external-provider/secret access in this router** (per its module docstring and
confirmed by trace).

### Legacy cosmetic — internal, `api_key`-protected (`routers/internal/sites.py`)
The router is **mounted at `/api/internal`** in `app/main.py`, so the live paths are
`/api/internal/sites/...`. The legacy client targets
`{base_platform_api_url}/internal/sites/...`, which resolves correctly only because
`base_platform_api_url` already includes `/api`.
- `GET  /api/internal/sites/locations` — site list for the cron to query.
- `POST /api/internal/sites/weather` — Weatherstack write-back into `sites_weather`.

### Calculation consumer
- `GET /api/telemetry/v2/sites/{site_id}/performance-context`
  (`routers/telemetry/v2.py`) — the unified chart endpoint that exposes the
  resolved weather curve + semantics to the frontend.

---

## 10. Frontend consumers

### Cosmetic (Weatherstack `sites_weather`)
- `…/operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/ActualProduction/ActualProduction.tsx`
  — reads `weather.weather_description` + `weather.weather_icon_url`; renders a
  "Observed weather (contextual)" tooltip + `WeatherIndicator` icon.
- `…/operations-and-maintenance/pages/CompanyDetails/tabs/Sites/Sites.tsx` — icon + tooltip per site row.
- `…/my-portfolio/pages/PortfolioPage/components/Sites.tsx` — icon + tooltip per site row.
- `components/common/WeatherIndicator/WeatherIndicator.tsx` — the shared icon component.
- Types: `src/api/operations-and-maintenance.ts` (`weather_description`, `weather_icon_url`).

### Native (physics / governance)
- `…/project-hub/pages/AssetManagementSiteDetails/tabs/Telemetry/PerformanceContextPanel.tsx` — performance + weather curve chart.
- `…/Telemetry/WeatherSemanticsPanel.tsx`, `WeatherDeclareDialog.tsx`, `WeatherDeclarationHistoryDialog.tsx` — governed semantics declaration UI (`ApiClient.weather.*`).
- API client: `src/api/telemetryV2.ts` (`getPerformanceContext`) + `ApiClient.weather.*`.

### Live verification observed (read-only, this dev DB, 2026-06-26)
- `sites_weather`: **2 rows** (sites **18**, **19**), `weather_icon_url` present,
  `weather_description` short strings (observed e.g. `72°F`, `68°F`), **last
  `updated_at` = 2026-04-16 10:00:01** → the cron has **not** refreshed this
  environment in ~10 weeks (consistent with the cron running only in GCP).
- `weather_observations` = **0**, `weather_sources` = **0**,
  `weather_source_profiles` = **0**, `weather_observation_batches` = **0**,
  `weather_device_mappings` = **0**, `expected_weather_provenance` = **0**.
  → In dev, the native domain is unused; the resolver falls back to W1 DAS for
  every site and weather is **never semantics-verified**.

---

## 11. Configuration / environment variables

| Variable | Where consumed | Status |
| --- | --- | --- |
| `weather_provider_access_key` | `backend/ilios-services/common/settings.py` | **Required by the legacy tier only.** Weatherstack API key. Loaded from `/etc/secrets/app_values_creds.yaml` (GCP secret). |
| `current_weather_api_url` | `backend/ilios-services/common/settings.py` | Default `https://api.weatherstack.com/current`. Legacy tier only. |
| `api_key`, `base_platform_api_url`, `environment_name`, `project_id` | `backend/ilios-services/common/settings.py` | Legacy tier ↔ main-app auth + targeting. |
| `WEATHER*` / `OPENWEATHER*` / `WEATHERSTACK*` / `SOLCAST*` / `NOAA*` / `NREL*` | — | **None present in `backend/ilios-server` settings.** The main app holds **no weather provider config or secret.** |
| Replit environment secrets | this workspace | **No weather secret present.** (`missing_secrets` are `UPSTASH_REDIS_*`, unrelated to weather.) So the legacy fetcher cannot run here even if invoked. |

**Consumed vs. unused:** the only *consumed* weather config is the legacy tier's
Weatherstack key/URL. The main app consumes **zero** weather configuration.

---

## 12. Expected-model dependencies

Weather enters the expected model through exactly one seam:

```
expected_service.compute_site_expected_period_effective
  → _load_bucket_inputs
      → WeatherResolver.resolve_window(...)        # the ONLY weather entry point
          → W2: weather_observations               (if an ACTIVE role=historical profile exists)
          → W1: telemetry_site_interval_rollups     (DAS, the live default fallback)
  → compute_expected_buckets / _expected_power_breakdown
```

- **Required inputs:** Plane-of-Array irradiance (**POA, W/m²**) and **cell
  temperature (°F)**.
- **`semantics_verified`** is set only when a governed `WeatherDeviceMapping`
  declares the stream as `poa` irradiance **and** `cell`/`module`/`modeled_cell`
  temperature. Unmapped DAS weather stays `unknown` and is **never assumed** to
  be POA/cell (no GHI→POA, no ambient→cell conversion).
- **Degradation** is applied inside the expected breakdown via an `age_factor`
  (in `expected_service._expected_power_breakdown`), layered on top of the
  weather-driven expected power.
- **Weatherstack/`sites_weather` is NOT consulted anywhere in this path.**

---

## 13. Weather-adjusted (WA) baseline dependencies

- The weather-adjusted baseline is validated/derived through the **same expected
  physics** seam (`baseline_physics_validation.py` + `expected_service`), which
  reads weather **only** via `WeatherResolver`.
- Baselines are derived from promoted `project_facts` (physics inputs) combined
  with resolver-provided weather; **SAFL is not a baseline source**, and
  **Weatherstack is not involved**.
- `expected_weather_provenance` (the table intended to snapshot which weather
  source drove a given expected/baseline computation) is **defined but never
  written** — so today there is **no persisted provenance link** from a WA
  baseline back to a specific weather source. This is a known forward gap (see §14).

---

## 14. Risks and technical debt

1. **Paid external dependency for cosmetic-only data.** Weatherstack is a paid
   API maintained solely to populate a description + icon. Ongoing cost +
   credential for near-zero functional value.
2. **Two competing "weather" concepts.** `sites_weather` (cosmetic) vs. the
   native provenance domain. The shared vocabulary invites confusion (e.g., a
   future reader could assume `sites_weather` feeds physics — it does not).
3. **Cross-repo / cross-tier coupling.** The Weatherstack fetcher lives in
   `backend/ilios-services` with its own deploy (Cloud Function + Cloud Scheduler
   via Terraform). It is **not runnable or visible** in the Replit dev
   environment, so it can silently drift from the main app (the
   `/internal/sites/weather` contract is the only coupling point).
4. **Stale cosmetic data in non-GCP environments.** In dev, `sites_weather` was
   last updated 2026-04-16 — any environment without the GCP cron shows stale or
   missing weather chips with no in-app way to refresh.
5. **Provenance loop incomplete.** `expected_weather_provenance` is a placeholder
   never written, so WA-baseline/expected computations don't persist which
   weather source drove them.
6. **Dead-ish provider surface.** `WeatherObservationBatchKind.provider_pull` and
   provider-type enums imply a future external-provider pull that is **not
   implemented**; they can mislead readers into thinking a provider client exists.
7. **No native ingestion scheduler.** W2 historical weather is manual-only; there
   is no automated refresh/backfill for the physics weather domain (by design
   today, but a gap if automated historical refresh is ever desired).
8. **Weatherstack fields are description/icon only.** Even though Weatherstack
   *can* return temperature/irradiance-adjacent fields, the current fetcher reads
   only `weather_descriptions[0]` + `weather_icons[0]`, so it could never be a
   physics source without code changes anyway.

---

## 15. Recommended cleanup plan (NOT executed — proposal only)

**Decision point first:** is the cosmetic site-card weather description/icon a
product requirement? The answer determines the path.

**Option A — Retire Weatherstack entirely (if cosmetic indicator is expendable).**
- Decommission the `fetch_sites_weather` Cloud Function + its Cloud Scheduler job
  (Terraform) and remove the `weather_provider_access_key` secret.
- Remove the `/internal/sites/locations` + `/internal/sites/weather` endpoints,
  `SiteWeatherCRUD`, the `sites_weather` table (migration), and the FE
  description/icon consumers (see §16).
- **Physics is untouched** (native W0/W1/W2 + DAS telemetry are independent).
- Result: removes a paid dependency, a live credential, and a cross-tier coupling.

**Option B — Keep the indicator, drop the paid provider.**
- Replace Weatherstack with a free/native source (e.g., derive a coarse
  description from existing DAS/temperature data, or a free weather API), keeping
  the `sites_weather` contract and FE unchanged.

**Option C — Status quo, documented.**
- Keep Weatherstack but record that it is cosmetic-only and isolated from physics
  (this document), and add an in-app "stale weather" indicator for non-GCP
  environments.

**Independent of the above:** consider implementing
`expected_weather_provenance` writes to close the provenance loop (§13), and
either implement or remove the `provider_pull` placeholder surface (§14.6). These
are native-domain improvements unrelated to Weatherstack.

> Recommended: **Option A or B**, gated on product confirmation that losing the
> cosmetic indicator (A) is acceptable. Engineering risk is low because no
> calculation depends on Weatherstack.

---

## 16. Files affected if cleanup is later approved

> **Reference only — none of these were modified in this audit.**

**Legacy tier (`backend/ilios-services`)**
- `services/fetch_sites_weather/` (function code, `sites_manager.py`, `cloudbuild.yaml`)
- `common/settings.py` (`current_weather_api_url`, `weather_provider_access_key`)
- `README.md` (Weatherstack reference)

**Infrastructure**
- `infra/ilios-infra/ilios-infra/template/gh-cloudbuild.tf` (Cloud Function + Cloud Scheduler job)
- GCP secret `app_values_creds.yaml` → `weather_provider_access_key`

**Main app (`backend/ilios-server`)**
- `app/routers/internal/sites.py` (`/sites/locations`, `/sites/weather`)
- `app/crud/site_weather.py` (`SiteWeatherCRUD`)
- `app/models/site.py` (`SiteWeather` model + `Site.weather` relationship)
- `app/schema/om_site.py` (`CreateSiteWeatherList`, `SitesLocationsList`)
- New Alembic migration to drop `sites_weather` (was created by `c21be722f5cc`)
- Any site-detail/O&M response schema that nests `weather`

**Frontend (`frontend/rea-investment-fe`)**
- `…/ActualProduction/ActualProduction.tsx`
- `…/CompanyDetails/tabs/Sites/Sites.tsx`
- `…/my-portfolio/pages/PortfolioPage/components/Sites.tsx`
- `components/common/WeatherIndicator/WeatherIndicator.tsx`
- `src/api/operations-and-maintenance.ts` (`weather_description`, `weather_icon_url` types)

**Native-domain optional improvements (separate from Weatherstack)**
- Implement writes to `expected_weather_provenance` in `expected_service` / baseline flow.
- Implement or remove the `provider_pull` ingestion placeholder.

---

## 17. Mutation boundaries

This sprint observed the following hard boundaries (all respected):

- **Read-only investigation only.** No production code, migrations, schema,
  config, API, or scheduler changes.
- **No weather refreshes.** The Weatherstack cron was not invoked; no
  `historical-import` or `refresh` endpoint was called.
- **No deletions.** Nothing was dropped or truncated.
- **No Site 4 mutations** (and no mutations to any site/company).
- **Database access was strictly `SELECT`/count** (§10) — zero writes, zero
  commits. Queries touched only metadata/aggregates and a 5-row sample.
- The **only file authored by this sprint** is **this document**
  (`docs/weather_data_source_audit.md`), the sprint's explicit deliverable; it is
  documentation, not production code. (The prompt file under `attached_assets/`
  was provided by the user, not created here.)

---

## 18. Browser validation plan (read-only)

To validate these findings interactively in a running dev environment **without
mutating anything**:

1. **Cosmetic weather (System A).** Open **O&M → Site Details → Overview** for a
   site that has a `sites_weather` row (e.g., site 18 or 19). Confirm the
   "Observed weather (contextual)" tooltip + `WeatherIndicator` icon render from
   `weather_description` / `weather_icon_url`. Repeat on **Company Details →
   Sites** and **My Portfolio → Sites** list rows. Note the values are static
   (last refreshed 2026-04-16 in dev).
2. **Physics weather (System B).** Open **Project Hub → Asset Management → Site
   Details → Telemetry**. Inspect `PerformanceContextPanel` (the weather/
   performance chart) and the **Weather Semantics** panel. With the native domain
   empty in dev, expect "no historical weather" / unverified-semantics states and
   weather sourced from DAS (W1).
3. **API spot-checks (GET only).** Call `GET /api/weather/sites/{id}/historical-readiness`
   and `GET /api/telemetry/v2/sites/{id}/performance-context` and confirm weather
   provenance/semantics fields. Do **not** call any `POST` (import/profile/
   declaration/refresh) endpoint.
4. **Scheduler check.** Confirm the app's only scheduler is the telemetry
   scheduler (`app/main.py` lifespan, gated by `telemetry_scheduler_enabled`) and
   that no weather scheduler exists in-app.
5. **DB read-only confirmation.** `SELECT` counts/last-update from `sites_weather`
   and the native `weather_*` tables (as in §10). No writes.

---

## 19. Confirmation: is Weatherstack still used?

**Yes — Weatherstack is still used, but only in the legacy
`backend/ilios-services` cloud-function tier, and only for cosmetic data
(weather description + icon) written to `sites_weather`.**

- It is the **only** live external weather API in the codebase.
- Its credential (`weather_provider_access_key`) is required **only** by that
  legacy tier; the main `backend/ilios-server` app and this Replit environment do
  **not** hold or consume it.
- It drives **no** physics, expected generation, weather-adjusted baseline, O&M
  math, reconciliation, or degradation.
- It is therefore **safe to remove from a data-integrity standpoint**; removal
  only affects a cosmetic site-card indicator and requires product sign-off
  rather than engineering risk acceptance (see §15–§16).

No other external weather provider (OpenWeather, NOAA, NREL, Solcast,
Tomorrow.io, Visual Crossing, Meteostat) is integrated anywhere.

---

## 20. Confirmation: no production code was changed

**No production code, migrations, schema, configuration, API, or scheduler was
changed during this audit.** No weather refreshes were triggered, no data was
deleted, and no Site 4 (or any site/company) records were mutated. Database
access was strictly read-only (`SELECT`/aggregates). The only file authored by
this sprint is `docs/weather_data_source_audit.md` — the explicit deliverable —
which is documentation, not production code.
