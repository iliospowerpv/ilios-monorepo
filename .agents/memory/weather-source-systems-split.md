---
name: Weather source systems split
description: iliOS weather = legacy Weatherstack (external/paid cosmetic) vs native W0/W1/W2 (physics) vs native observed_condition (telemetry-derived cosmetic, dual-run with Weatherstack); never conflate.
---

iliOS weather data comes from two systems that must never be conflated:

1. **Legacy Weatherstack (cosmetic ONLY).** Lives exclusively in the separate
   `backend/ilios-services` GCP cloud-function tier (`common/settings.py`,
   `services/fetch_sites_weather/`). A GCP Cloud Scheduler cron (`0 * * * *`)
   calls `api.weatherstack.com/current` and reads ONLY `weather_descriptions[0]`
   + `weather_icons[0]` (no temp/irradiance), POSTing them to the main app's
   `/api/internal/sites/weather` (mounted at `/api/internal`; client uses a base
   URL ending in `/api`) → `SiteWeatherCRUD.create_items` (append, NOT upsert) →
   `sites_weather` table. UI reads the latest row via `Site.latest_weather_info`
   (relationship ordered by `updated_at` desc). Consumed only by cosmetic FE
   chips/tooltips (ActualProduction widget, CompanyDetails/Portfolio site lists,
   `WeatherIndicator`). Requires the `weather_provider_access_key` secret — held
   ONLY in the services tier, never in `ilios-server` or the Replit env.

2. **Native W0/W1/W2 provenance domain (PHYSICS).** Pure PostgreSQL in
   `ilios-server` (`app/models/weather.py` 7 tables, `app/services/weather/*`,
   `/api/weather/*`). NO external provider, secret, BigQuery, or Firestore.
   Weather enters calculations ONLY via `WeatherResolver.resolve_window`
   (consumed by `expected_service._load_bucket_inputs`): W2 `weather_observations`
   if an ACTIVE role=historical profile exists, else W1 DAS
   `telemetry_site_interval_rollups`. Inputs: POA W/m² + cell temp °F;
   `semantics_verified` only with a `WeatherDeviceMapping` declaring poa +
   cell/module/modeled_cell. Native ingestion is MANUAL only
   (`POST /api/weather/sites/{id}/historical-import`) — there is NO weather
   scheduler (the only in-app scheduler is the telemetry one).
   `expected_weather_provenance` is a defined-but-runtime-unwritten placeholder.

**Why it matters:** the shared word "weather" invites the wrong assumption that
`sites_weather`/Weatherstack feeds physics. It does NOT. Weatherstack is safe to
remove from a data-integrity standpoint (drives zero calc); removal only drops a
cosmetic FE indicator, so it needs product sign-off, not engineering risk.

**How to apply:** when asked "where does weather come from / is Weatherstack
used / can we drop it", separate cosmetic (`sites_weather`, services tier) from
physics (native domain, resolver). No other external weather provider
(OpenWeather/NOAA/NREL/Solcast/Tomorrow.io/Visual Crossing/Meteostat) is
integrated; NREL/PVWatts/PVGIS hits are PVsyst document-parsing prompts.
Full write-up: `docs/weather_data_source_audit.md`.

**Native cosmetic-indicator replacement (IMPLEMENTED, dual-run):**
The cosmetic `WeatherIndicator` (ActualProduction + the two site-card `Sites.tsx`)
now shows a native telemetry-derived **`observed_condition`**, NOT `sites_weather`.
Single source of truth: `native_weather_condition_service.derive_site_condition`
(pure, query-free) fed by `solar_position.py` (zenith + Haurwitz clear-sky GHI).
Surfaced two ways: (a) single-site via the read-only `performance-context`
envelope (FE `useNativeWeatherCondition` hook); (b) site lists via
`company_helper._extend_with_observed_condition` (batched latest-irradiance), set
on a TRANSIENT `site.observed_condition` attr serialized under the existing
`weather` alias in `om_site.py` (NEVER mutates the read-only `site.weather`).
**Weatherstack still runs unchanged (dual-run)** — `sites_weather` is just no
longer the indicator's source. So when debugging "why does the weather chip show
X", look at the native service / performance-context, not `sites_weather`.
Honesty rules enforced: null ≠ 0 (no irr ⇒ "unavailable"); never "rainy" (wettest
= `overcast_unknown` → "precipitation (undetermined)"); **never imply POA/cell
unless `plane_governed`** (raw `irradiance_wm2` merges POA+GHI, plane unknown).
Sites have IANA `timezone` but **no numeric lat/long — only `lon_lat_url` (URL
VARCHAR)**, hence the tiered algorithm (clear-sky index when coords parse, else
irradiance-magnitude + local-time night detection). Design:
`docs/native_weather_indicator_replacement_audit.md`. Decommission Weatherstack
only AFTER dual-run validation + product sign-off.
