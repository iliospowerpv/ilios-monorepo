---
name: Weather source systems split
description: iliOS has TWO disjoint weather systems — legacy Weatherstack (cosmetic) vs native W0/W1/W2 (physics); they share no code/storage/creds.
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
