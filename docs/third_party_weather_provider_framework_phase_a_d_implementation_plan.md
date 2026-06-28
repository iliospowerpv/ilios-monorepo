# Third-Party Weather Provider Framework — Phases A–D Implementation Plan

**Status:** IMPLEMENTATION PLANNING ONLY. Nothing in this document is built. No
code, no migrations run, no API keys, no provider contracts. Everything labelled
"PROPOSED" is for review/approval only.

**Companion to:** `docs/third_party_weather_provider_framework_audit.md` (the audit
that established the architecture and the eligibility gate).

**Scope (this plan):** Phases **A–D** only — a provider framework for
**context / provenance / cosmetic** use. Sites *without usable telemetry weather*
can pull external weather, store it auditably, and surface it (clearly labelled
"modeled / context-only"), with **zero** path into expected/baseline physics.

**Out of scope (explicitly excluded):** expected-eligibility; GHI→POA transposition;
ambient→cell modeling; any `WeatherResolver` behaviour change; baseline math; WS.5;
scheduler automation.

> ## HARD RULE (governs the entire plan)
> External GHI / ambient data is **context-only**. It may populate provenance,
> readiness *context*, and the cosmetic indicator (labelled "modeled"). It must
> **never** become an input to `WeatherResolver`'s physics path or expected/baseline
> math unless a future, separately-approved governed physics model (transposition +
> temperature) is built. That future work is **not** part of A–D.

---

## Grounding (verified against live code)

- Weather router: `app/routers/weather.py` → `weather_router = APIRouter()` mounted at
  `/api/weather`; writes gated by `telemetry_admin_required` +
  `get_authorized_site_with_company_admin` + `_enforce_company_visibility`; reads by
  `get_authorized_site`.
- Existing ingestion: `app/services/weather/historical_weather_import_service.py`
  (`preview_import` / `run_historical_import`) — all-or-nothing, idempotent on
  `dedupe_key`, naive-UTC. **The only weather ingestion that exists; no network pull
  anywhere.**
- Model home: `app/models/weather.py` (7 tables, 12 enums). `WeatherSourceType`
  already has `external_modeled_provider`; `WeatherObservationBatchKind` already has
  `provider_pull`. **The value-storage primitives already exist.**
- Adapter template: `app/integrations/telemetry/base.py` (`@runtime_checkable`
  Protocols + structured exceptions `CredentialError`/`RateLimited`/`ProviderUnavailable`/
  `NoData`/`MappingError`; dataclasses in `.models`), `registry.py` (`get_adapter` via
  `importlib` from a catalog `adapter_class`), `credential_store.py`
  (`GCPSecretManagerCredentialStore`, `is_credential_store_durable`,
  `_block_if_storage_not_durable`).
- Resolver seam (DO NOT TOUCH): `WeatherResolver.resolve_window` →
  `expected_service._load_bucket_inputs` consumes only POA W/m² + cell °F.
- Migration convention: `app/alembic/versions/ffNN_<slug>.py`; current head **`ff37`**
  → next proposed revision **`ff38`**.

---

## 1. Phased implementation plan

Each phase is independently shippable and additive. Dependencies are explicit. Every
phase ends with the **resolver-invariance gate** (§11) passing.

### Phase A — Catalog + adapter scaffolding (NO network, NO secrets)

Goal: the plumbing exists and is unit-tested with fixtures, but nothing pulls live
data yet and nothing is surfaced.

| Task | Deliverable | Depends on | Acceptance |
|---|---|---|---|
| A1 | `weather_provider_catalog` model + `weather_provider_pull_status_enum` (model only; migration in §2) | — | Model imports; `Base.metadata` emits one new table; no behaviour change. |
| A2 | `app/integrations/weather/base.py`: `WeatherProviderAdapter` Protocol, `WeatherProviderCapabilities`, `WeatherPullResult`, structured exceptions (mirror telemetry) | — | `@runtime_checkable`; pure types, no I/O. |
| A3 | `app/integrations/weather/registry.py`: `get_weather_adapter(provider_key, db)` via `importlib` from catalog `adapter_class` | A1, A2 | Resolves a fixture adapter; raises clean error for unknown/disabled. |
| A4 | First adapter `app/integrations/weather/openmeteo_adapter.py` (keyless, free) — parse only, fed by recorded fixtures | A2 | GHI fixture → rows with `irradiance_plane=ghi`, `temperature_type=ambient`, `is_modeled=true`; **never** `poa`/`cell`. |
| A5 | Catalog seed (idempotent) for Open-Meteo (`is_enabled=false` by default) | A1 | Re-running seed is a no-op; dedupe by `provider_key`. |

**Phase A exit:** adapters parse fixtures correctly; nothing networked; no routes; no
UI; resolver/expected untouched.

### Phase B — Credentials + provider accounts (keyed providers)

Goal: keyed providers can have accounts stored durably by reference; free/keyless
providers need none.

| Task | Deliverable | Depends on | Acceptance |
|---|---|---|---|
| B1 | `weather_provider_accounts` model (mirror `DASConnection`; stores `secret_name` reference only) | A1 | No secret column exists; only a GCP reference. |
| B2 | Reuse telemetry `CredentialStore` (do NOT build a second secret system) with a weather secret-name prefix `ilios-weather-c{company}-…` | B1 | `store()`/`read()`/`delete()` via existing GCP store; `is_credential_store_durable()` honored. |
| B3 | Account CRUD (`WeatherProviderAccountCRUD`) + schemas | B1 | Create/list/pause/archive; no hard delete. |
| B4 | Account routes + `test_credentials` (see §3); durability gate + license gate | B2, B3 | In-memory store → keyed-account create blocked in prod with honest error; compensating secret delete on DB-commit failure. |

**Phase B exit:** keyed accounts can be created (durably) and credential-tested;
keyless providers work without an account; no pull yet.

### Phase C — Provider pull + import pipeline (DB-as-cache, idempotent, context-only)

Goal: pull external weather over a bounded window into `weather_observations` via a
`provider_pull` batch — gap-filling, idempotent, honest on failure.

| Task | Deliverable | Depends on | Acceptance |
|---|---|---|---|
| C1 | `provider_import_service.py`: `preview_provider_import` (dry-run) + `run_provider_import` (write) mirroring historical import | A3, A4 | Reuses `WeatherObservationCRUD.upsert` (`ON CONFLICT DO NOTHING`); all-or-nothing per chunk. |
| C2 | Gap computation: only request timestamps absent for `(site, source, metric)` | C1 | Re-pull of a stored window writes 0 rows. |
| C3 | Bounded/chunked backfill clamped to provider `max_history_days`; per-chunk checkpoint | C1 | Long windows chunk; failure resumes same gap. |
| C4 | Batch provenance: `batch_kind=provider_pull` + additive batch columns (`account_id`, `pull_status`, hashes, api_version, `error_summary`) | C1, §2 | Partial/failed pull recorded on batch; **no fabricated rows**. |
| C5 | Rate-limit + backoff + quota (Redis token bucket per `provider_key`+account) | C1 | 429 → backoff + failed batch, never bad data; quota cap refuses pull. |
| C6 | Import routes (preview + run + batch list) — see §3 | C1–C5 | Preview shows row count, semantics, **eligibility verdict = "context-only"**, est. cost/quota, before any write. |

**Phase C exit:** operators can pull external weather into the DB auditably; idempotent;
honest failures; still no expected-math reachability.

### Phase D — Read-only context / provenance / cosmetic surfacing

Goal: make imported external weather *visible and auditable* without changing any
eligibility computation.

| Task | Deliverable | Depends on | Acceptance |
|---|---|---|---|
| D1 | Read-only **External Weather Context** response (per site): active external sources, coverage windows, last pull status, batch list | C4 | Pure read; does **not** call/alter `compute_weather_readiness`. |
| D2 | Surface in readiness panel as a clearly separated **"Context (not expected-eligible)"** section | D1 | Existing readiness verdict (POA+cell) byte-identical before/after. |
| D3 | (Optional) cosmetic indicator may consume external **modeled** value as a labelled fallback ("modeled — Open-Meteo") only when no telemetry-derived value exists | D1 | Never shows modeled data as POA/measured; null stays null, never 0; "rainy"-class labels never invented. |
| D4 | FE provider admin: provider list + account form (rendered from `config_schema`) + import preview/run dialog with the context-only verdict shown prominently | C6 | Verdict and licensing class visible before import. |

**Phase D exit:** users can see and trust external weather as context; the expected
pipeline and readiness eligibility are provably unchanged.

---

## 2. Migrations proposed (review only — NOT run)

One additive, reversible Alembic revision **`ff38_weather_provider_framework`**
(down_revision = `ff37`):

1. **Create enum** `weather_provider_pull_status_enum` = {`succeeded`, `partial`,
   `failed`} (`create_type`).
2. **Create table `weather_provider_catalog`** (see §4).
3. **Create table `weather_provider_accounts`** (see §4).
4. **Add nullable columns to `weather_observation_batches`** (all `NULL`, no backfill):
   `account_id` (FK → `weather_provider_accounts.id`, `ON DELETE SET NULL`),
   `pull_status` (enum, nullable), `provider_request_hash` (String),
   `provider_response_hash` (String), `provider_api_version` (String),
   `error_summary` (Text).
5. `downgrade()` drops the columns, tables, and enum in reverse.

**Migration invariants:** additive only; no existing column altered/dropped; no data
backfill; fully reversible; no change to any other table (`weather_observations`,
`weather_sources`, `weather_source_profiles`, `weather_source_approvals`,
`weather_device_mappings`, `expected_weather_provenance`, telemetry tables) — the
existing `external_modeled_provider` source type and `provider_pull` batch kind
already cover external providers.

---

## 3. Routes proposed

All additive, under the existing `/api/weather` `weather_router`; auth identical to
the existing weather surface.

| Phase | Method | Path | Auth | Purpose |
|---|---|---|---|---|
| A/D | GET | `/providers` | `get_current_user` (any authed) | List enabled providers + capabilities + licensing class (from catalog). Read-only. |
| B | POST | `/companies/{company_id}/weather-provider-accounts` | `telemetry_admin_required` + company-admin + visibility | Create keyed account (durability + license gate; store secret by reference). |
| B | POST | `/companies/{company_id}/weather-provider-accounts/{account_id}/test` | same | `test_credentials`; update `credential_status`. |
| B | PATCH | `/companies/{company_id}/weather-provider-accounts/{account_id}` | same | Pause/archive/rotate (no hard delete). |
| C | POST | `/sites/{site_id}/provider-import/preview` | `telemetry_admin_required` + `get_authorized_site_with_company_admin` + visibility | Dry-run pull: row count, semantics, **context-only verdict**, est. cost/quota. **No writes.** |
| C | POST | `/sites/{site_id}/provider-import` | same | Execute bounded pull → `provider_pull` batch (gap-filling, idempotent). |
| C/D | GET | `/sites/{site_id}/provider-import/batches` | `get_authorized_site` | List provider batches + `pull_status` for audit. |
| D | GET | `/sites/{site_id}/external-weather-context` | `get_authorized_site` | Read-only context: sources, coverage, last pull, **"not expected-eligible"** banner. |

Profile creation/approval reuse the **existing** weather profile/approval endpoints
unchanged — an external source is governed by the same routes that already exist.

---

## 4. Models proposed (additive, in `app/models/weather.py`)

### `weather_provider_catalog` (mirrors `TelemetryProviderCatalog`)
`id`, `provider_key` (String, unique, NOT NULL), `display_name` (String, NOT NULL),
`adapter_class` (String, NOT NULL — dotted import path), `config_schema` (JSONB —
drives credential forms; empty for keyless), `capabilities_json` (JSONB — snapshot of
`WeatherProviderCapabilities`), `licensing_class` (String:
`public_domain`/`free_attribution`/`free_noncommercial`/`commercial`), `is_enabled`
(Boolean, default `false`), `created_at`, `updated_at`.

### `weather_provider_accounts` (mirrors `DASConnection`; keyed providers only)
`id`, `company_id` (FK companies, CASCADE, NOT NULL), `provider_key` (String, NOT
NULL), `display_name` (String), `secret_name` (String — **GCP reference only, never
the key**), `status` (active/paused/archived), `credential_status`
(unverified/verified/invalid/expired), `last_sync_status` (never/success/partial/
failed), `last_sync_at` (nullable), `licensing_acknowledged_by` (FK users, SET NULL),
`licensing_acknowledged_at` (nullable), `created_at`, `updated_at`.

### `weather_observation_batches` (additive columns only — see §2.4)
`account_id`, `pull_status`, `provider_request_hash`, `provider_response_hash`,
`provider_api_version`, `error_summary`. All nullable.

**No new `weather_observations` columns** — `is_modeled`, `confidence`,
`irradiance_plane`, `temperature_type`, `dedupe_key` already capture everything an
external value needs.

---

## 5. Auth model

- **Reads** (`/providers`, batch list, external-weather-context): `get_authorized_site`
  / `get_current_user` — any user authorized for the site/company.
- **Writes** (account create/test/patch, import preview/run): `telemetry_admin_required`
  **AND** `get_authorized_site_with_company_admin` **AND** `_enforce_company_visibility`
  (defense in depth) — identical to the existing weather write surface.
- **Durability gate:** reuse `_block_if_storage_not_durable` — in production-like envs,
  refuse to create a *keyed* account when the credential store is in-memory.
- **License gate:** a company must acknowledge licensing (commercial providers) before
  an account is usable; recorded on the account row + approval ledger.
- **Secrets:** only via the existing GCP `CredentialStore`; the DB stores references.
  No keys in code, logs, responses, or this document.

---

## 6. Provider capability contract (PROPOSED — `app/integrations/weather/base.py`)

Mirrors `app/integrations/telemetry/base.py` exactly (same exception taxonomy,
`@runtime_checkable` Protocols, dataclasses in a sibling `.models`).

```text
# Structured exceptions (reuse telemetry taxonomy, weather namespace)
WeatherProviderError(Exception)            # base, carries provider_key
  ├─ WeatherCredentialError                # 401/403
  ├─ WeatherNoData                         # success, empty
  ├─ WeatherProviderUnavailable            # 5xx / transport
  ├─ WeatherRateLimited(retry_after?)      # 429
  └─ WeatherMappingError                   # unknown location/site

@runtime_checkable
WeatherProviderAdapter(Protocol):
    provider_key: str
    def capabilities(self) -> WeatherProviderCapabilities: ...
    def test_credentials(self, credentials: Mapping[str,str]) -> TestResult: ...
    def get_observations(
        self, credentials: Mapping[str,str], *,
        latitude: float, longitude: float,
        window_start: datetime, window_end: datetime,
        requested_metrics: Sequence[str],
        granularity: str = "hourly",
    ) -> WeatherPullResult: ...

@dataclass(frozen=True)
WeatherProviderCapabilities:
    supports_historical: bool
    supports_forecast: bool
    metrics: frozenset[str]                  # {"ghi","dni","dhi","gti_poa","air_temp",...}
    native_plane: WeatherIrradiancePlane     # poa | ghi | dni | dhi | unknown
    native_temperature_type: WeatherTemperatureType  # ambient | modeled_cell | unknown
    is_modeled: bool
    min_granularity_minutes: int
    max_history_days: int | None
    rate_limit: RateLimitSpec                 # rpm, rpd, max_concurrent
    licensing_class: str
    # Derived, READ-ONLY, ALWAYS False in Phases A–D:
    #   expected_eligible_capable -> only a future governed POA+temp model can flip this

@dataclass(frozen=True)
WeatherPullResult:
    rows: Sequence[NormalizedWeatherRow]      # obs_ts, metric, value, unit, plane,
                                              # temperature_type, is_modeled, confidence
    partial: bool
    warnings: tuple[str, ...]
    request_hash: str
    response_hash: str
    api_version: str | None
```

**Contract invariants:**
- An adapter MUST set `native_plane`/`native_temperature_type` honestly; it MUST NOT
  emit `poa`/`cell` for data that is physically GHI/ambient.
- `is_modeled=true` for satellite/NWP sources; carried through to source/batch/obs.
- Partial pulls are reported via `partial`/`warnings`; **a missing reading is an
  absent row, never a fabricated/zero value.**
- `expected_eligible_capable` is structurally **False** for every provider shipped in
  A–D (enforced by the gate, not by trust).

---

## 7. Test plan

- **Adapter unit (no network):** each adapter parses recorded fixtures → assert
  plane/temp/unit/confidence; GHI providers yield `ghi`/`ambient` (never `poa`/`cell`).
  Use `monkeypatch`/`respx`-style stubs (no `pytest-mock` in repo).
- **Eligibility gate:** importing any A–D provider does NOT make
  `WeatherResolver.resolve_window` return it as expected input; `expected_eligible_capable`
  is False for all seeded providers.
- **Idempotency/backfill:** re-running a pull writes 0 rows (`dedupe_key` conflict);
  partial failure → `pull_status=partial`, 0 fabricated rows; chunked backfill resumes
  the same gap.
- **Rate-limit/backoff:** limiter blocks past quota; 429 → backoff + failed batch.
- **Credential/durability:** in-memory store blocks keyed-account create in prod;
  compensating secret delete on DB-commit failure; secret never appears in responses.
- **RESOLVER-INVARIANCE (gate):** golden expected-math + readiness outputs are
  **byte-identical** before and after the framework exists, with and without an
  imported external source present. This is the release gate for every phase.
- **Provenance:** every observation traces obs → batch → source → (account); approvals
  append-only.
- **Harness:** ilios-server pytest needs `test_db_name` env + own DB; run focused with
  `-o addopts=""` to bypass coverage gate.

---

## 8. Browser validation

1. **Provider catalog/account (Phase B/D):** `/providers` lists providers + licensing
   class; create a keyless Open-Meteo source; keyed account form renders from
   `config_schema`; durability gate blocks keyed create on in-memory storage (honest
   error, not silent success).
2. **Preview before import (Phase C):** run preview on a no-weather site → shows row
   count, GHI/ambient semantics, and a prominent **"Context-only — not
   expected-eligible"** verdict + licensing/cost; confirm nothing is written.
3. **Import + audit (Phase C/D):** execute pull → `provider_pull` batch appears with
   `pull_status`; readiness panel still reports site as **not** expected-ready;
   external value visible only in the "Context" section, labelled "modeled".
4. **Honesty/negative:** kill network mid-pull → batch `partial/failed`, no fabricated
   rows; cosmetic indicator stays "unavailable", never "0".
5. **Regression:** a DAS-ready site shows identical charts/expected values after the
   framework exists (resolver unchanged).
6. **Auth:** admin surfaces require login; plan an authenticated walkthrough (these
   panels are not reachable unauthenticated).

---

## 9. Cost / licensing controls

- **DB-as-cache:** `weather_observations` is the cache; gap-only pulls + `dedupe_key`
  idempotency prevent redundant metered calls.
- **Per-account quotas:** daily/min call caps in Redis; refuse pulls that would breach;
  surface remaining quota in the UI.
- **Preview-before-import:** every pull is previewable (row count + estimated calls/cost
  class) before spending quota.
- **Licensing class on the catalog** (`public_domain`/`free_attribution`/
  `free_noncommercial`/`commercial`) + a required **licensing acknowledgement** on keyed
  accounts; commercial providers stay `is_enabled=false` until legal sign-off.
- **First build is keyless Open-Meteo** (free) for internal evaluation — zero spend,
  exercises the full pipeline.
- **No provider is contracted and no key is provisioned by this plan.**

---

## 10. Mutation boundaries

**WRITES introduced by A–D (and nothing else):**
- INSERT into `weather_provider_catalog` (seed; idempotent).
- INSERT/UPDATE `weather_provider_accounts` (account lifecycle; never the secret value).
- INSERT into GCP Secret Manager (via existing store; reference returned to DB).
- INSERT `weather_observation_batches` (`batch_kind=provider_pull`) + the new nullable
  columns.
- INSERT `weather_observations` via `ON CONFLICT DO NOTHING` (append/idempotent only).
- INSERT `weather_sources` (one per external provider source; non-secret).
- INSERT `weather_source_approvals` (existing ledger) when a profile/account is approved.

**STRICTLY FORBIDDEN in A–D:**
- No write to `weather_observations` that mutates/overwrites/deletes existing rows.
- No write to `expected_weather_provenance` (stays dormant).
- No change to `weather_device_mappings` / declaration governance (WS layer untouched).
- No change to `WeatherResolver`, `expected_service`, `compute_expected_buckets`,
  `BucketInput`, or any physics coefficient.
- No change to `compute_weather_readiness`'s eligibility logic (Phase D adds a
  *separate* read-only context surface; it does not alter the POA+cell verdict).
- No scheduler/daemon; all pulls are manual/API-triggered.
- No GHI→POA or ambient→cell conversion anywhere.
- No secret stored in DB, logs, or responses.

---

## 11. Confirmation: expected math remains unchanged

- The **only** route into expected math is `WeatherResolver.resolve_window` →
  `_load_bucket_inputs` → `compute_expected_buckets` (POA W/m² + cell °F). Phases A–D
  add **no** resolution path and change **no** resolver code.
- External providers in A–D land as `irradiance_plane=ghi` / `temperature_type=ambient`
  (or `unknown`); the resolver's existing POA-only / cell-only physics test refuses
  them. They are therefore unreachable by expected math **by construction**, not by
  policy.
- `expected_eligible_capable` is structurally **False** for every provider shipped in
  A–D.
- A **resolver-invariance golden test** (§7) is the release gate for each phase:
  expected-math and readiness-eligibility outputs must be byte-identical before/after
  the framework exists and whether or not an external source is imported.
- Any future expected-eligibility (POA-native providers + governed transposition +
  temperature model) is **Phase E**, separately approved, and outside this plan.

---

## Appendix — constraint compliance checklist

| Constraint | Compliance |
|---|---|
| Do not implement yet | Plan only; no code/migrations/keys. |
| Context/provenance/cosmetic only | Phases A–D deliver exactly this; D is read-only context + labelled cosmetic. |
| Exclude expected eligibility | `expected_eligible_capable` always False; resolver untouched. |
| Exclude GHI→POA / ambient→cell | No conversion anywhere; semantics carried honestly. |
| Exclude WeatherResolver changes | No resolver code touched; invariance gate enforces it. |
| Exclude baseline math | `compute_expected_buckets`/coefficients untouched. |
| Exclude WS.5 | Declaration/governance layer not modified. |
| Exclude scheduler automation | All pulls manual/API; no daemon. |
| External GHI/ambient stays context-only | Enforced structurally (gate + resolver POA-only test). |
