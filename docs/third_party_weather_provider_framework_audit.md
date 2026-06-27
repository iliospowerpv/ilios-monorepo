# Third-Party Weather Provider Framework — Audit / Design Sprint

**Status:** AUDIT / DESIGN ONLY. No production code, no migrations, no API keys, no
paid-provider commitment, no behavior changes were made as part of this sprint.
Everything below labelled "PROPOSED" is for review only and is **not** implemented.

**Objective:** Design a provider-agnostic weather ingestion framework so that sites
*without usable telemetry weather* (no POA irradiance sensor, no cell/module
temperature, or no DAS weather at all) can still obtain auditable weather inputs —
**without** changing the expected/baseline math or `WeatherResolver` behaviour, and
without ever fabricating weather.

**Author's headline conclusion:** The native W0/W2 weather domain is *already*
storage- and provenance-ready for external providers. An imported external value is
just a `weather_observation` tied to a `weather_source` of type
`external_modeled_provider`, governed by a `weather_source_profile` and an approval
ledger entry. The real gaps are (1) a **provider adapter + credential + pull**
layer (none exists for weather today — all native weather is file/manual import),
and (2) a **physics-eligibility gate**: nearly every external provider delivers GHI
(horizontal irradiance) and ambient temperature, which W0 explicitly forbids
treating as POA / cell temperature. So the safe, honest design lets external
providers *populate provenance, readiness context, and the cosmetic indicator
immediately*, while **expected-math eligibility stays blocked** until a governed
transposition (GHI→POA) and temperature model are designed and approved in a later
phase (WS-track work, out of scope here).

---

## 0. Scope, constraints, and how this document is grounded

This audit was produced by reading the live code in `backend/ilios-server`:
`app/models/weather.py`, `app/services/weather/*` (resolver, historical import,
profile, readiness, declaration), `app/routers/weather.py`, `app/crud/weather.py`,
`app/schema/weather.py`, plus the Telemetry V2 provider stack
(`app/models/telemetry.py`, `app/integrations/telemetry/*`,
`app/routers/telemetry/v2.py`) which is the template for the proposed provider
layer, and the expected-math seam in
`app/services/telemetry/expected_service.py`.

### Hard constraints honoured (restated, for the record)

- No implementation; no API keys; no paid-provider commitment.
- No expected-model changes; no baseline math changes.
- No `WeatherResolver` *behaviour* changes **yet** (design only).
- No WS.5; no weather-declaration changes.
- No migrations except as **proposals for review**.
- Never fabricate weather. **Unavailable remains unavailable** unless a
  governed/approved source exists.
- Additive only when eventually built.

### Two "weather" systems this design must not conflate

1. **Legacy Weatherstack** — cosmetic only, lives in the *separate*
   `backend/ilios-services` cloud-function tier, writes `sites_weather`, drives
   zero physics. **Out of scope; untouched.**
2. **Native W0/W1/W2 provenance domain** — pure PostgreSQL in `ilios-server`; the
   only path by which weather can ever reach expected math (via `WeatherResolver`).
   **This is the system the new providers plug into.**

(There is also the recently shipped native *cosmetic* `observed_condition`
indicator, derived from telemetry irradiance; it is a read-only consumer, not a
weather source, and is unaffected by this design.)

---

## 1. Current architecture

### 1.1 The data model (`app/models/weather.py`) — 7 tables, 12 enums

| Table | Purpose | Append/immutable? | Key columns |
|---|---|---|---|
| `weather_sources` | Source **identity** + non-secret provider metadata. Global / company / site scoped. | Deactivated, never deleted (`active`). | `source_type`, `display_name`, `provider_key`, `is_modeled`, `default_confidence`, `licensing_note` |
| `weather_source_profiles` | Effective-dated, per-site **source policy** (which source drives which role over what window). | Versioned by **new row**; never mutated. **No single-active constraint** — overlaps allowed, ordered by `priority`. | `role`, `weather_source_id`, `priority`, `effective_from/to`, `fallback_allowed`, `external_modeled_allowed`, `min_confidence_policy`, `status`, `approved_by/at` |
| `weather_observation_batches` | Immutable **import provenance** (one row per import/pull). | Immutable; corrected by superseding batch. | `batch_kind`, `period_start/end`, `row_count`, `unit_system`, `source_file_id`, `superseded_by_batch_id` |
| `weather_observations` | Non-telemetry weather **values** (imported/modeled/manual). NOT a `telemetry_readings` replacement. | Append/idempotent on unique `dedupe_key`. Missing = **absent row**, never fabricated. | `metric`, `value`, `unit`, `obs_ts` (naive-UTC), `irradiance_plane`, `temperature_type`, `is_modeled`, `confidence`, `dedupe_key` |
| `weather_source_approvals` | Append-only **approval ledger**. Polymorphic (`target_type`,`target_id`), no FK so it's never cascade-deleted. | Immutable (no `updated_at`). | `action`, `approved_by/at`, `rationale` |
| `weather_device_mappings` | Governed **measurement semantics** for *telemetry/device* weather (plane / temp type / calibration). | Effective-dated + governed lifecycle (draft→active→superseded), DB-enforced single-active per lineage. | `irradiance_plane`, `temperature_type`, `calibration_status`, `declaration_status`, `declaration_basis`, `needs_re_review`, `upstream_fingerprint_json` |
| `expected_weather_provenance` | Forward placeholder to snapshot which source drove an expected calc. | **Defined but written by no runtime today.** | `expected_calc_id`, `weather_source_id`, `source_profile_id`, `snapshot_meta_json` |

**Enums of note for this design:** `WeatherSourceType` already includes
`external_modeled_provider`, `imported_historical_provider_file`, and
`unavailable`. `WeatherSourceProfileRole` = {`live`, `historical`, `design`,
`fallback`}. `WeatherIrradiancePlane` = {`poa`, `ghi`, `dni`, `dhi`, `unknown`} —
**only `poa` is physics-usable today** (no transposition model exists).
`WeatherTemperatureType` = {`cell`, `module`, `modeled_cell`, `ambient`,
`unknown`} — **`ambient` is not usable** as cell temp. `WeatherConfidence` =
{high, medium, low, unknown}.

### 1.2 The services (`app/services/weather/`)

- `historical_weather_import_service.py` — all-or-nothing, idempotent **file/manual**
  import. `preview_import` (dry-run) and `run_historical_import` (write).
  Normalises timestamps to naive-UTC and builds `dedupe_key`s. This is the only
  existing ingestion path — **there is no provider/network pull anywhere in the
  weather domain.**
- `weather_profile_service.py` — `WeatherSourceProfile` lifecycle:
  `create_historical_profile` (drafts) and `apply_profile_action`
  (`approve`/`reject`/`revoke`/`supersede`), each appending to the approval ledger.
  **No auto-activation.**
- `weather_readiness_service.py` — computes whether a site/window has enough
  *physics-usable* weather (POA + cell temp) for an expected replay; reports
  coverage gaps against the expected bucket grid.
- `declaration_service.py` + `declaration_policy.py` — governed lifecycle for
  `weather_device_mappings`; `evaluate_declaration` decides
  `expected_model_eligible` from basis + physics-usability + calibration. (This is
  the **WS governance layer; out of scope to change**, but it is the precedent for
  how external-provider semantics should eventually be gated.)

### 1.3 The resolver and the expected-math seam (the line we must not move)

`WeatherResolver.resolve_window(site_id, start, end, bucket_size="1h")` in
`app/services/weather/weather_resolver.py` is the **single** read-only seam:

1. **W2 path (historical):** if an **active** `role=historical` profile exists *and*
   physics-usable approved `weather_observations` are found → return them.
2. **W1 path (DAS fallback):** otherwise read `telemetry_site_interval_rollups`
   (live DAS), excluding `role=historical` profiles.

It returns a `ResolvedWeatherWindow` dataclass:
- `buckets: dict[datetime, ResolvedWeatherBucket]` where each bucket carries
  `irradiance_poa_wm2` and `cell_temperature_f`.
- `provenance: ResolvedWeatherProvenance` (`status`, `source_type`, `source_label`,
  `is_modeled`, `confidence`, `irradiance_plane`, `temperature_type`,
  `calibration_status`, `weather_source_id`, `profile_id`, `profile_role`,
  `min_confidence_policy`, `missing_inputs`, `warnings`, `indicators`).

`provenance.status` becomes `semantics_verified` only when a governed mapping
declares `irradiance_plane=poa` **and** a cell-usable temperature type, with no
conflicts and full window coverage; otherwise `legacy_das_unverified`.

`expected_service._load_bucket_inputs` (≈ line 584) calls the resolver and maps
each bucket into a `BucketInput(irradiance_wm2=…poa…, cell_temperature_f=…)`. The
physics in `compute_expected_buckets` → `_expected_power_kw` expects **POA W/m²**
and **cell temperature °F**.

> **The seam, precisely:** any new provider's data reaches expected math **only**
> by becoming a `ResolvedWeatherWindow` whose buckets are POA W/m² + cell °F. We
> add provider *resolution paths* and *ingestion*; we do **not** touch
> `BucketInput`, `compute_expected_buckets`, or the physics coefficients.

### 1.4 Telemetry V2 provider stack (the template to mirror)

The provider layer we need for weather already exists for telemetry and should be
mirrored, not reinvented:

- **Catalog:** `TelemetryProviderCatalog` (`app/models/telemetry.py`) — DB rows with
  `provider_key`, `display_name`, `adapter_class` (dotted import path),
  `config_schema` (JSONB; drives dynamic credential forms), `is_enabled`.
- **Adapter abstraction:** `ProviderAdapter` Protocol
  (`app/integrations/telemetry/base.py`) with `test_credentials`, `list_sites`;
  optional `ReadingsAdapter` Protocol with `get_readings(...) -> ReadingsPullResult`.
  Resolved at runtime by `get_adapter` via `importlib` from `adapter_class`.
- **Credentials:** `CredentialStore` abstraction
  (`app/integrations/telemetry/credential_store.py`); `GCPSecretManagerCredentialStore`
  writes JSON creds to GCP Secret Manager and returns a `secret_name` reference; the
  DB row (`DASConnection`) stores **only the reference**, never the secret.
  `is_credential_store_durable()` is `True` only for GCP. `_block_if_storage_not_durable`
  refuses to create accounts in production when storage is in-memory.
- **Three-state account model:** account `status` (active/paused/archived),
  `credential_status` (unverified/verified/invalid/expired), `last_sync_status`
  (never/success/partial/failed).
- **Account creation:** `POST /v2/companies/{company_id}/provider-accounts` →
  visibility check → durability gate → license check → `credential_store.store(...)`
  → DB row with `secret_name` → compensating secret-delete if the DB commit fails.

---

## 2. Provider abstraction design (PROPOSED)

Goal: one interface, many providers, zero special-casing in the resolver or import
service. Mirror the telemetry adapter pattern exactly so we reuse the registry,
credential store, durability gate, and licensing precedent.

### 2.1 New capability: `WeatherProviderAdapter`

A Protocol in a proposed `app/integrations/weather/base.py` (mirrors
`integrations/telemetry/base.py`):

```text
WeatherProviderAdapter (Protocol)            # capability-typed, structural
  provider_key: str
  capabilities() -> WeatherProviderCapabilities
  test_credentials(credentials) -> TestResult
  get_observations(                            # the core pull
      credentials, *, latitude, longitude,
      start, end, requested_metrics, granularity
  ) -> WeatherPullResult
```

`WeatherProviderCapabilities` (a plain dataclass) declares, per provider, what the
provider can *honestly* return — this is what powers the eligibility gate:

```text
WeatherProviderCapabilities
  supports_historical: bool          # backfill window
  supports_forecast: bool
  metrics: set[str]                  # e.g. {"ghi","dni","dhi","gti_poa","air_temp",...}
  native_plane: WeatherIrradiancePlane          # poa | ghi | unknown
  native_temperature_type: WeatherTemperatureType  # ambient | modeled_cell | unknown
  is_modeled: bool                   # satellite/NWP model vs ground station
  min_granularity_minutes: int
  max_history_days: int | None
  rate_limit: RateLimitSpec
  licensing_class: "public_domain" | "free_attribution" | "free_noncommercial" | "commercial"
```

`WeatherPullResult` carries normalized rows
(`obs_ts`, `metric`, `value`, `unit`, `plane`, `temperature_type`, `is_modeled`,
`confidence`) **plus the raw provider payload hash** for provenance, **plus
`partial`/`warnings`** so a partial pull is recorded honestly (never silently
zero-filled).

### 2.2 Concrete adapters (one file each, lazily imported)

`app/integrations/weather/openmeteo_adapter.py`, `noaa_adapter.py`,
`meteostat_adapter.py`, `visualcrossing_adapter.py`, `tomorrowio_adapter.py`,
`solcast_adapter.py`, … each implementing `WeatherProviderAdapter`. Registration is
implicit via the catalog's `adapter_class` column (same as telemetry). No adapter is
loaded unless its catalog row is enabled and selected.

### 2.3 The normalize→persist pipeline reuses W2 verbatim

A provider pull is just a programmatic import:

```
adapter.get_observations(...)            # network I/O, provider-specific
  → normalize to WeatherObservation rows  # metric/unit/plane/temp/confidence
  → WeatherObservationBatch(batch_kind = provider_pull)   # already an enum value
  → WeatherObservationCRUD.upsert(... on_conflict_do_nothing(dedupe_key))
```

No new storage primitives are required for the *values*. The only new persistence is
the **provider account/credential** record (§3) and a **provider catalog** row (§9).

### 2.4 The eligibility gate (the honesty crux)

`native_plane` / `native_temperature_type` from the adapter flow straight into the
observation's `irradiance_plane` / `temperature_type`. Therefore:

- A provider that returns **GHI + ambient** (Open-Meteo, NOAA, Meteostat, Visual
  Crossing default, Tomorrow.io) lands as `irradiance_plane=ghi`,
  `temperature_type=ambient`. The resolver's existing physics-usability test (POA +
  cell) **will not pick these for expected math** — exactly the desired behaviour.
  They remain visible for provenance, readiness *context*, and the cosmetic
  indicator.
- A provider that returns **plane-of-array / tilted irradiance (GTI/POA)** and a
  **modeled cell/module temperature** (Solcast GTI, SolarAnywhere, DTN/Vaisala
  enterprise) can land as `irradiance_plane=poa`,
  `temperature_type=modeled_cell` — but **only** becomes expected-eligible through
  the **existing governed declaration/approval flow**, never automatically.

This is what keeps "unavailable remains unavailable": importing Open-Meteo does not
make a site expected-ready; it only makes the *gap* auditable and, if approved for
cosmetic/context use, visible.

---

## 3. Credential model (PROPOSED)

Reuse the telemetry `CredentialStore` and GCP Secret Manager wholesale — do **not**
build a second secret system.

- **New table `weather_provider_accounts`** (company-scoped) mirrors `DASConnection`:
  `company_id`, `provider_key`, `display_name`, `secret_name` (GCP reference only —
  **never the key**), `status` (active/paused/archived), `credential_status`
  (unverified/verified/invalid/expired), `last_sync_status`, `last_sync_at`,
  `licensing_acknowledged_by/at`.
- **Secrets live only in GCP Secret Manager**, keyed like
  `ilios-weather-c{company}-{rand}`. The DB stores the reference; reads go through the
  store. This matches the existing W0 rule "NEVER store API keys in
  `weather_sources`."
- **Durability gate:** reuse `is_credential_store_durable()` /
  `_block_if_storage_not_durable` — in production-like envs, refuse to create a
  weather provider account when the store is in-memory.
- **Free / keyless providers** (Open-Meteo, NOAA) need **no** account row to *pull*,
  but still need a `weather_sources` row for provenance and a governed profile to be
  used. The account table is only for keyed providers.
- **No keys are added in this sprint.** The design only specifies *where* a future
  key would live (GCP, by reference) and *how* it would be requested (via the
  platform secret request flow, mirroring telemetry), never inline.

---

## 4. Provider priority / fallback model (PROPOSED)

The data model **already supports this** and needs no new columns:
`weather_source_profiles` has `role`, `priority`, `effective_from/to`,
`fallback_allowed`, `external_modeled_allowed`, and `min_confidence_policy`, with
**no single-active constraint** by design (overlaps allowed, ordered by priority).

Proposed resolution order inside a future `WeatherResolver` extension (design only —
not changing current behaviour):

1. **On-site calibrated / governed DAS POA + cell** (W1, `semantics_verified`) — always wins.
2. **Approved historical import** (W2 file) for the window.
3. **External provider observation** (W2 provider_pull) **only** if:
   - an **active** profile references it,
   - the profile's `external_modeled_allowed = true`,
   - the provider value is physics-usable (POA + cell/modeled_cell) **and** governed
     eligible, and
   - it satisfies the profile's `min_confidence_policy`.
4. Otherwise → **unavailable** (honest N/A; never substitute GHI-as-POA, never 0).

`priority` breaks ties between multiple eligible external sources (e.g. Solcast
priority 10 > a free fallback priority 100). `fallback_allowed` lets an operator say
"use the modeled provider only when the primary sensor is dark." **All of this is
opt-in per site via approved profiles** — there is no global auto-fallback.

---

## 5. Provenance requirements (PROPOSED, mostly already satisfied)

Every external value must be traceable end-to-end. The W0 model already gives us
most of this; the additions are small and additive:

- **Source identity:** a `weather_sources` row (`source_type=external_modeled_provider`,
  `provider_key`, `is_modeled=true`, `licensing_note`).
- **Batch:** every pull = one `weather_observation_batches` row
  (`batch_kind=provider_pull`, `period_start/end`, `row_count`, `unit_system`).
  **Proposed additive columns** (review only): `provider_request_hash`,
  `provider_response_hash`, `provider_api_version`, `account_id` (FK to
  `weather_provider_accounts`), `pull_status` (succeeded/partial/failed),
  `error_summary`.
- **Observation:** `is_modeled`, `confidence`, `irradiance_plane`,
  `temperature_type` already capture semantics; `dedupe_key` keeps re-pulls
  idempotent.
- **Approval:** using an external source for anything beyond cosmetic display goes
  through `weather_source_approvals` (profile activation) — already append-only.
- **Expected provenance:** the dormant `expected_weather_provenance` table is the
  right home to later snapshot "which source/profile drove this expected calc."
  **Not written in this sprint** (consistent with W0).

---

## 6. Caching & rate-limit strategy (PROPOSED)

External weather APIs are rate-limited and (for paid tiers) metered, so we must
avoid redundant calls and respect quotas:

- **DB as the cache of record:** `weather_observations` *is* the cache. Before any
  pull, compute the missing sub-windows (gaps) for `(site, source, metric)` and only
  request those — re-pulling an already-stored window is a no-op via
  `dedupe_key` `ON CONFLICT DO NOTHING`.
- **Per-provider rate limiter:** a `RateLimitSpec` on each adapter
  (requests/minute, requests/day, max concurrent) enforced centrally before the HTTP
  call. Reuse Redis (already a project dependency) for a token-bucket counter keyed
  by `provider_key` + account.
- **Short-TTL response cache** (Redis) for *forecast/now* endpoints to coalesce
  bursts; **historical** pulls don't need a TTL cache because the DB is durable.
- **Backoff + circuit breaker:** exponential backoff on 429/5xx; record failures on
  the batch (`pull_status=failed`, `error_summary`) and on the account
  (`credential_status`/`last_sync_status`) — **never** write fabricated observations
  on failure.
- **Quota awareness:** store per-account daily call counts; surface remaining quota
  in the admin UI; refuse pulls that would breach a configured cap.

---

## 7. Import / backfill strategy (PROPOSED)

- **One pipeline, two triggers.** Reuse the existing all-or-nothing, idempotent
  import semantics from `historical_weather_import_service`; add a *provider-sourced*
  variant that produces `batch_kind=provider_pull` instead of `file_import`.
- **Preview/dry-run first** (mirror `preview_import`): show the operator how many
  rows, what plane/temp semantics, what licensing/cost class, and what the
  eligibility verdict will be (almost always "context-only" for GHI providers)
  **before** any write.
- **Bounded, chunked backfill:** clamp each request to the provider's
  `max_history_days` and chunk long windows; checkpoint per chunk so a failure
  resumes the same gap (same pattern as telemetry ingestion's cursor).
- **Gap-filling, not overwriting:** only fetch timestamps absent from
  `weather_observations`; existing rows are never mutated (corrections = superseding
  batch).
- **Manual-only to start.** No scheduler in this design (the only in-app scheduler
  is telemetry's, and the constraints forbid scheduler changes). A future,
  separately-approved `weather_scheduler_enabled` flag could automate pulls — **noted
  as out of scope, not designed here.**

---

## 8. Governance / approval model (PROPOSED, reuses existing ledger)

- **Cosmetic/context use** of an external source (e.g. show "modeled GHI ~620 W/m²"
  on the indicator, or list it in readiness context) requires the source to exist
  and be `active`, but does **not** make it expected-eligible.
- **Expected-eligible use** requires the **full existing governance chain**:
  1. a `weather_source_profiles` row (role `historical` or `fallback`) with
     `external_modeled_allowed=true`, reaching `active` only via an explicit
     `apply_profile_action(approve)` — logged in `weather_source_approvals`;
  2. physics-usable semantics (POA + cell/modeled_cell) — for providers that emit
     GHI/ambient this is **impossible without a future governed transposition model**,
     which is intentionally **not** part of this sprint (WS-track);
  3. a licensing acknowledgement (commercial providers) recorded on the account.
- **Modeled-data discipline:** `is_modeled=true` is carried on the source, batch, and
  observation; a profile must opt in via `external_modeled_allowed` before modeled
  data is ever resolvable — the W0 invariant "modeled weather is never silently
  substituted" is preserved.
- **Separation of duties / audit:** all approvals are append-only with `rationale`;
  revocation is an action, not a delete.

---

## 9. Required DB / model changes (PROPOSED — migrations for review only)

> All additive. No existing column is altered or dropped. No migration is applied in
> this sprint.

1. **`weather_provider_catalog`** (new) — mirrors `TelemetryProviderCatalog`:
   `provider_key` (unique), `display_name`, `adapter_class`, `config_schema` (JSONB),
   `capabilities_json` (JSONB snapshot of `WeatherProviderCapabilities`),
   `licensing_class`, `is_enabled`.
2. **`weather_provider_accounts`** (new) — keyed-provider accounts (see §3); stores a
   GCP `secret_name` reference only.
3. **`weather_observation_batches`** additive columns (see §5):
   `account_id` (FK), `provider_request_hash`, `provider_response_hash`,
   `provider_api_version`, `pull_status`, `error_summary`. All nullable.
4. **No change** to `weather_observations`, `weather_sources`,
   `weather_source_profiles`, `weather_source_approvals`,
   `weather_device_mappings`, or `expected_weather_provenance` schemas — the existing
   `external_modeled_provider` source type, `provider_pull` batch kind, plane/temp
   enums, and profile policy columns already cover external providers.
5. **Migration shape (for review):** one additive Alembic revision creating tables 1
   & 2 and the nullable columns in 3; `create_type` for any new enum (e.g. a small
   `weather_pull_status_enum`); no data backfill; fully reversible. **Do not run.**

---

## 10. API / routes needed (PROPOSED)

Mirror the telemetry V2 provider routes; all under `/api/weather`, all behind
`telemetry_admin_required` + company/site visibility (matching the existing weather
router), all additive:

| Method | Path | Purpose |
|---|---|---|
| GET | `/providers` | List enabled providers + capabilities + licensing class (from catalog). |
| POST | `/companies/{company_id}/weather-provider-accounts` | Create keyed account (durability + license gate; store secret by reference). |
| POST | `/companies/{company_id}/weather-provider-accounts/{id}/test` | `test_credentials`; update `credential_status`. |
| PATCH/DELETE | `/…/weather-provider-accounts/{id}` | Pause/archive/rotate (no hard delete). |
| POST | `/sites/{site_id}/provider-import/preview` | Dry-run a provider pull; return row counts, semantics, eligibility verdict, est. cost/quota. |
| POST | `/sites/{site_id}/provider-import` | Execute a bounded provider pull → `provider_pull` batch (gap-filling, idempotent). |
| GET | `/sites/{site_id}/provider-import/batches` | List provider batches + `pull_status` for audit. |

Profile creation/approval and readiness/resolver **reuse existing endpoints
unchanged** — an external source is governed by the *same* profile/approval routes
that already exist.

---

## 11. Testing plan (PROPOSED)

- **Adapter unit tests (no network):** each adapter parses a **recorded fixture**
  payload into normalized rows; assert correct plane/temp/unit/confidence and that
  GHI providers yield `irradiance_plane=ghi` / `temperature_type=ambient` (never
  silently `poa`/`cell`). Use `responses`/`respx`-style HTTP stubbing or monkeypatch
  (project has no `pytest-mock`; use `monkeypatch`).
- **Eligibility gate tests:** importing a GHI provider must **not** make
  `WeatherResolver` return it as expected input; a POA+modeled_cell provider must
  still require an active governed profile before becoming expected-eligible.
- **Idempotency/backfill tests:** re-running a pull writes zero new rows
  (`dedupe_key` conflict); a partial failure records `pull_status=partial` and writes
  no fabricated rows.
- **Rate-limit/backoff tests:** limiter blocks past quota; 429 triggers backoff and a
  failed batch, not bad data.
- **Resolver invariance tests (critical):** with no governed external profile, golden
  expected-math outputs are **byte-identical** before/after the framework exists —
  proving `WeatherResolver` behaviour is unchanged.
- **Provenance tests:** every observation traces to a batch → source → (account);
  approvals are append-only.
- **Harness notes (from prior work):** ilios-server pytest needs the `test_db_name`
  env + its own DB; override the coverage addopts (`-o addopts=""`) for focused runs.

## 12. Browser validation plan (PROPOSED)

- **Admin: provider catalog & account** — `/providers` lists providers with licensing
  class; create a *keyless* (Open-Meteo) source and a *keyed* account form renders
  from `config_schema`; durability gate blocks keyed-account creation when storage is
  in-memory (verify honest error, not a silent success).
- **Preview before import** — run a provider-import preview on a no-weather site;
  confirm it shows row counts, GHI/ambient semantics, and a **"context-only — not
  expected-eligible"** verdict; confirm nothing is written.
- **Import + audit** — execute the pull; confirm a `provider_pull` batch appears with
  `pull_status`, the readiness panel still reports the site as **not** expected-ready
  (GHI can't drive physics), and the cosmetic indicator can show the modeled value
  *labelled as modeled*, never as POA.
- **Negative/honesty checks** — kill the network mid-pull → batch shows
  `partial/failed`, **no** fabricated observations, indicator stays "unavailable" not
  "0".
- **Regression** — a site already expected-ready via DAS shows **identical** charts
  and expected values after the framework is present (resolver unchanged).
- **Note:** the weather admin surfaces are behind auth; validation requires a logged-in
  session, so plan for an authenticated walkthrough (the cosmetic indicator and these
  admin panels are not reachable from the unauthenticated screen).

## 13. Risks / cost / licensing

### 13.1 Provider evaluation matrix

| Provider | Cost / tier | Key? | Irradiance | Temp | History | Native plane | Expected-eligible *as-is*? | Licensing caution |
|---|---|---|---|---|---|---|---|---|
| **Open-Meteo** | Free; commercial tier paid | No (free) | GHI, DNI, DHI; **GTI/tilted available** | air (ambient) | ✓ (ERA5 reanalysis) + forecast | ghi (poa only if GTI requested) | **No** as GHI; *maybe* via GTI **but modeled + needs governance** | CC-BY; **non-commercial** on free tier — commercial use needs paid plan |
| **NOAA** (NWS/NSRDB) | Free (public domain) | No / token | GHI (NSRDB), forecast | ambient | ✓ (NSRDB historical, US) | ghi | **No** (GHI, US-only) | Public domain; **US coverage only**; NSRDB has latency |
| **Meteostat** | Free / freemium | No / key | limited radiation | ambient | ✓ (station historical) | ghi/unknown | **No** | Mixed CC-BY-NC; station gaps; sparse irradiance |
| **Visual Crossing** | Commercial (paid; small free tier) | Yes | GHI ("solarradiation") | ambient | ✓ | ghi | **No** (GHI) | Commercial license; metered |
| **Tomorrow.io** | Commercial | Yes | GHI; limited history | ambient | partial | ghi | **No** (GHI) | Commercial; history limited on lower tiers |
| **Solcast** | Commercial (research/free tiers historically) | Yes | **GTI / POA**, GHI, DNI, DHI | air; can model cell | ✓ (satellite-modeled) | **poa** (GTI) | *Potentially* — POA + governance + license | Commercial; solar-specialist; modeled |
| **Enterprise** (SolarAnywhere/Clean Power Research, DTN, Vaisala) | Commercial (expensive) | Yes | **POA + module temp models** | modeled_cell/module | ✓ | **poa** | *Potentially* — strongest physics fit + governance | Heavy licensing/cost; contractual |

**Takeaway:** the *free* providers (Open-Meteo, NOAA, Meteostat) are excellent for
**provenance, gap visibility, and cosmetic/context** use, but deliver GHI/ambient and
therefore **cannot** drive expected math under W0 rules. Only **solar-specialist /
enterprise** providers that natively deliver **POA (GTI) + modeled cell temperature**
are even candidates for expected-eligibility — and only behind the existing governed
declaration/approval flow plus a (future) transposition design.

### 13.2 Key risks

- **Silent semantic drift (highest risk):** mislabeling GHI as POA would corrupt
  expected math. Mitigated structurally — the adapter sets the plane honestly and the
  resolver's POA-only test refuses GHI; no code path converts GHI→POA in this design.
- **Licensing/compliance:** non-commercial / attribution terms (Open-Meteo free,
  Meteostat, some NOAA derivatives) vs. iliOS's commercial use. Mitigation:
  `licensing_class` on the catalog + a required licensing acknowledgement on keyed
  accounts; legal sign-off before enabling any commercial provider.
- **Cost overrun (paid APIs):** metered calls. Mitigation: DB-as-cache, gap-only
  pulls, per-account quotas, preview-before-import.
- **Geographic / latency gaps:** NOAA US-only; reanalysis lag; station sparsity.
  Mitigation: per-provider `max_history_days`/coverage in capabilities; honest
  "unavailable" when out of coverage.
- **Secret handling:** mitigated by reusing GCP Secret Manager by reference + the
  durability gate; no keys in DB or this doc.
- **Scope creep into expected math:** mitigated by the resolver-invariance golden
  tests and by deferring transposition/temperature modeling to a separate WS phase.

### 13.3 Cost posture for this sprint

Zero. No provider is contracted, no key is provisioned, no metered call is made.
A recommended **first build** uses **Open-Meteo (keyless, free, non-commercial — for
internal evaluation only)** to exercise the *plumbing* end-to-end while proving the
eligibility gate keeps it out of expected math.

---

## 14. Implementation phases (PROPOSED — each separately approved)

> Sequenced so every phase is additive, independently shippable, and dual-runs beside
> the untouched resolver/expected math. Nothing here is started in this sprint.

- **Phase A — Catalog & adapter scaffolding (no network):** add
  `weather_provider_catalog`, the `WeatherProviderAdapter` Protocol + capabilities,
  the registry/resolver (mirror telemetry), and one **keyless** Open-Meteo adapter
  with fixture-only unit tests. No routes wired to live pulls yet.
- **Phase B — Credentials & accounts:** add `weather_provider_accounts`, reuse
  `CredentialStore`/GCP + durability gate, account CRUD + `test_credentials` route.
- **Phase C — Pull + import pipeline:** provider-sourced import producing
  `provider_pull` batches (gap-filling, idempotent, bounded/chunked), preview route,
  rate-limit/backoff/quotas, batch provenance columns.
- **Phase D — Context surfaces (read-only, honest):** show imported external weather
  in readiness *context* and (clearly labelled "modeled") in the cosmetic indicator —
  **without** touching expected eligibility. This is where free providers deliver
  user value safely.
- **Phase E — (Gated, future, separate approval) Expected-eligibility for POA-native
  providers:** design a governed GHI→POA transposition + cell-temperature model and a
  declaration basis so *only* solar-specialist/enterprise POA sources, fully approved,
  can reach `WeatherResolver`'s W2 path. **This is the only phase that could ever
  change resolver behaviour and is explicitly out of scope here (WS-track).**
- **Phase F — (Optional, future) Automation:** a separately-approved
  `weather_scheduler_enabled` flag for periodic pulls. Out of scope now.

**Phases A–D deliver the full "providers for sites without telemetry weather" value
for cosmetic/context/provenance use with zero risk to expected math. Phase E is the
only one that interacts with physics and is deferred.**

---

## Appendix — Constraint compliance checklist

| Constraint | How this design complies |
|---|---|
| No implementation | Design doc only; nothing built. |
| No API keys | None added; keys would live in GCP by reference (future). |
| No paid-provider commitment | Providers evaluated, none contracted; first build is keyless Open-Meteo. |
| No expected-model / baseline math changes | `BucketInput`, `compute_expected_buckets`, coefficients untouched. |
| No `WeatherResolver` behaviour changes yet | New paths are Phase E, gated + deferred; A–D don't alter resolution. |
| No WS.5 / no weather-declaration changes | Governance reuses existing ledger/declaration as-is; no edits proposed. |
| No migrations unless proposed for review | §9 migrations are review-only, additive, reversible, **not run**. |
| Never fabricate weather | Failures record partial/failed batches; no rows written; null≠0 preserved. |
| Unavailable stays unavailable unless governed/approved | GHI providers never become expected-eligible; only governed POA sources can, via existing approval flow. |
