# Third-Party Weather Provider Framework — Phase D.5: Operational Readiness & Governance (Implementation Plan)

> **Status: IMPLEMENTATION PLANNING ONLY.** No code, schema, endpoints, or UI are
> changed by this document. It is the design that must be approved before any D.5
> build work begins.

## 0. Scope & Hard Guardrails (carried from Phases A–D)

Phase D.5 adds the **operational governance layer** required before a production
rollout of the context-only weather provider framework. It is purely additive
operational tooling around the existing pipeline. The following invariants are
**non-negotiable** and every item below is designed to preserve them:

- **Do NOT modify `WeatherResolver`.** Its window resolution, source selection, and
  POA-only/cell-only physics test are untouched.
- **Do NOT modify expected math** (`expected_service`, `compute_expected_buckets`,
  `compute_site_expected_period_effective`).
- **Do NOT modify baseline calculations** (draft/active baselines, design points).
- **Do NOT introduce GHI→POA transposition.**
- **Do NOT introduce ambient→cell conversion.**
- **Do NOT begin Phase E** (any physics use of external weather).
- **Do NOT add scheduler automation.** All pulls remain operator-triggered. Any
  notification is emitted **inline** at the moment of an operator action, never by a
  background poller.
- **Do NOT change the backend `Site` entity.**
- **Maintain the context-only invariant:** external observations stay
  `irradiance_plane ∈ {ghi, unknown}` / `temperature_type ∈ {ambient, unknown}`,
  `physics_usable_rows == 0`, and never become expected-eligible.

A dedicated **Invariant Preservation Matrix** (§13) maps each invariant to the D.5
mechanism that protects it, with the test that proves it.

---

## 1. Current State (grounded baseline — what A–D already gives us)

Understanding exactly what exists prevents re-building governance that is already
present. Migration head for the weather domain is `ff38_weather_provider_framework`
(foundation in `ff32_weather_provenance_foundation`). The branched Alembic tree also
shows other leaf heads (`ff01`, `ff07`, `ff25`), so a **merge migration** may be
required (see §11).

### 1.1 Data model that already exists
- **`weather_provider_catalog`** (global registry): `provider_key`, `display_name`,
  `adapter_class`, `config_schema`, `capabilities_json` (holds quota/rate-limit
  hints), `licensing_class`, `docs_url`, `is_enabled` (default **false**),
  `created_at`, `updated_at`. **No approval state, no provider version column, no
  archive, no lifecycle audit.**
- **`weather_provider_accounts`** (per-company credential reference): `status`
  (`active`/`paused`/`archived`), `credential_status`
  (`unverified`/`verified`/`invalid`/`expired`), `last_sync_status`
  (`never`/`success`/`partial`/`failed`), `licensing_acknowledged_by/at`,
  `last_success_at`, `last_error_at`, `last_error_message`, `is_archived`,
  `archived_at`, `created_by_user_id`. **Account-level health is largely already
  modeled.** **No quota/rate-limit counters.**
- **`weather_observation_batches`** (immutable provenance per pull): `account_id`,
  `pull_status` (`succeeded`/`partial`/`failed`), `provider_request_hash`,
  `provider_response_hash`, `provider_api_version`, `error_summary`, `row_count`,
  `period_start/end`, `created_at`. **No `queued`/`running` states, no `trigger`,
  no retry lineage** (batches are deliberately immutable).
- **`weather_observations`**: idempotent on `dedupe_key`
  (`INSERT … ON CONFLICT DO NOTHING`). Replay-safe by construction.
- **`weather_source_profiles`** / **`weather_source_approvals`**: governed
  draft→approved→active→superseded lifecycle + append-only approve/reject/revoke
  ledger — but scoped to **site-level sources**, not catalog providers.
- **Cross-cutting**: generic `AuditLog` (`models/audit_log.py`, `AuditLogCRUD`,
  `audit_middleware.py`); telemetry audit helpers (`helpers/telemetry/audit.py`).

### 1.2 API that already exists (`routers/weather.py`)
- `GET /providers` (catalog list)
- `GET/POST/PATCH /companies/{cid}/weather-provider-accounts[...]`
- `POST .../accounts/{aid}/test` (credential verification)
- `POST /sites/{sid}/provider-import/preview` (dry-run — reusable as "re-preview")
- `POST /sites/{sid}/provider-import` (write; durability + licensing gated)
- `GET /sites/{sid}/provider-import/batches` (paginated history)
- `GET /sites/{sid}/external-weather-context` (read-only provenance incl. recent
  batches + coverage)
- **Gates**: default-deny licensing (`_licensing_requires_ack` +
  `_UNRESTRICTED_LICENSING_CLASSES`); durability gate
  (`_block_if_storage_not_durable` in `production/prod/staging/stage/live`);
  `_resolve_provider_pull_context` enforces catalog `is_enabled`, account
  ownership/active, credential retrieval, licensing ack.

### 1.3 Frontend that already exists
- `WeatherProviderAdminSection.tsx`, `AddWeatherProviderAccountDialog.tsx`
  (portfolio admin).
- `ExternalWeatherContextPanel.tsx` (context-only banner + "Recent pulls" table),
  `ImportExternalWeatherDialog.tsx` (project Telemetry tab).
- Types in `src/types/weather.ts`; React Query hooks in `src/hooks/weatherProvider.ts`.

### 1.4 Patterns to mirror (do not reinvent)
- **`TelemetrySyncJob`** (`scope`/`status`/`trigger`, queued→running→succeeded/
  partial/failed) → model for a weather import-job record.
- **`weather_source_approvals`** append-only ledger → model for catalog lifecycle
  audit (rollback = reverse entry, never mutate).
- **`/health`** endpoint pattern (`routers/health.py`) → framework liveness.
- Structured-log event names (e.g. `telemetry_v2_fingerprint_lookup_failed`).
- **Do NOT mirror** `TelemetrySchedulerState`/lease model — that is automation,
  forbidden here.

---

## 2. Gap Analysis by Focus Area

| # | Focus area | Already present | Gap to close in D.5 |
|---|---|---|---|
| 1 | **Provider lifecycle** | `is_enabled` flag; account status/archive | Catalog enable/disable/approve/suspend/retire **endpoints**; approval state; append-only lifecycle audit; rollback = reverse transition; safe-disable semantics (block new pulls, retain data) |
| 2 | **Provider health** | Account `last_success_at`/`last_error_at`/`last_error_message`/`credential_status`/`last_sync_status`; per-batch `provider_api_version`/hashes | Quota usage + rate-limit status (best-effort, honest N/A); aggregated health rollup endpoint; catalog provider version column; API-health surfacing |
| 3 | **Operational dashboards** | `external-weather-context` (recent batches, coverage); `provider-import/batches` | Success/failure **trend** metrics; company-wide coverage/gap metrics; import **job** history (richer than immutable batches) |
| 4 | **Administrative tooling** | `preview` (dry-run); idempotent import | Retry failed import (job lineage); re-preview window (reuse preview); compare two batches (read-only diff); safe provider disable; archive/retire catalog provider |
| 5 | **Monitoring** | `logging.getLogger`; account error fields; Mailgun configured | Structured event logs; read-only metrics endpoints; **inline** failure notifications (no poller); framework health endpoint |
| 6 | **Disaster recovery** | `dedupe_key` idempotency; immutable batches | Backup/restore validation runbook; documented replay procedure; integrity-verification endpoint; duplicate-detection report |
| 7 | **Production readiness** | Default-off providers; default-deny licensing; durability gate | Migration readiness (additive/nullable + merge); rollout sequencing; rollback plan; smoke tests; operational runbooks |

---

## 3. Implementation Plan (phased sub-tracks)

D.5 is sequenced so the **rollout-blocking** governance lands first and the
observability/DR niceties follow. Each sub-track is independently shippable and
default-off.

### D.5a — Governance core (rollout-blocking)
1. Catalog lifecycle columns + `weather_provider_catalog_audit` append-only table.
2. Catalog lifecycle endpoints (enable/disable/approve/suspend/retire/restore +
   read-only audit) under a **platform-admin** guard (catalog is global — see §12).
3. `weather_provider_import_job` table (mirrors `TelemetrySyncJob`) wrapping the
   existing import write; **synchronous** execution (no scheduler), `trigger ∈
   {manual, retry, re_preview}`.
4. Retry endpoint (idempotent re-run of the same window; new job with
   `parent_job_id`).
5. FE: catalog lifecycle controls + rationale prompts + lifecycle audit drawer in
   `WeatherProviderAdminSection`.

### D.5b — Observability
6. Read-only metrics/coverage/gap endpoints (per-site + per-company).
7. Integrity-verification + batch-compare endpoints.
8. Aggregated provider-health rollup + framework health endpoint.
9. FE: import-history view (jobs + trend sparkline + coverage/gap), per-batch
   actions (retry/re-preview/compare/integrity), operational dashboard section.
10. Structured event logging across import + lifecycle paths.

### D.5c — Notifications & DR
11. Opt-in, **inline** Mailgun notifications on import failure / credential expiry
    (default OFF; emitted at operator-action time, never by a poller).
12. DR runbooks: restore validation, replay procedure, integrity check, duplicate
    detection.

---

## 4. Required Schema Additions

All additions are **additive and nullable-only** (or have a safe server default),
introduce no FK that re-parents existing rows, and never alter resolver/expected
inputs. No row is rewritten; an optional backfill only fills NULL operational
columns and is guarded (see §11).

### 4.1 `weather_provider_catalog` — new columns (nullable / defaulted)
- `approval_state` — new enum `weather_provider_approval_state`
  {`draft`, `approved`, `suspended`, `retired`}, server default `draft`.
- `provider_version` `VARCHAR` (adapter/contract version; distinct from the
  per-pull `provider_api_version` already on batches).
- `enabled_by_user_id`, `enabled_at`, `disabled_by_user_id`, `disabled_at`.
- `approved_by_user_id`, `approved_at`.
- `retired_at`, `is_archived` `BOOL` default `false`, `archived_at`.
- Quota/rate-limit **defaults** stay in `capabilities_json` (no change).

> `is_enabled` is retained but becomes **governed** (flipped only through the
> lifecycle endpoints, which also write the audit row). Direct DB flips remain
> possible for break-glass but are discouraged.

### 4.2 New table `weather_provider_catalog_audit` (append-only ledger)
Mirrors `weather_source_approvals`. **Rollback = append a reverse action; rows are
never mutated or deleted.**
- `id`, `provider_key` (FK → catalog), `action` enum
  {`enable`, `disable`, `approve`, `suspend`, `retire`, `archive`, `restore`,
  `version_bump`}, `actor_user_id`, `occurred_at`, `from_state`, `to_state`,
  `rationale` (`TEXT`), `metadata_json` (`JSONB`), `created_at`.

### 4.3 New table `weather_provider_import_job` (mirrors `TelemetrySyncJob`)
Batches stay immutable provenance; jobs carry attempt lifecycle + retry lineage so
nothing pollutes the batch table.
- `id`, `site_id` (FK), `account_id` (FK, nullable for keyless), `provider_key`,
  `scope` (`site`), `status` enum
  {`queued`, `running`, `succeeded`, `partial`, `failed`},
  `trigger` enum {`manual`, `retry`, `re_preview`} (**no `scheduled`**),
  `requested_window_start/end`, `effective_window_start/end`,
  `rows_attempted`, `rows_written`,
  `batch_id` (FK → `weather_observation_batches`, nullable),
  `parent_job_id` (FK → self, nullable; retry lineage),
  `idempotency_key` `VARCHAR` (deterministic hash of
  site+provider+account+normalized-window+trigger),
  `error_summary` (`TEXT`), `created_by_user_id`,
  `created_at`, `started_at`, `finished_at`.

**Concurrency / idempotency controls (required):**
- A **partial unique index** on `idempotency_key` for jobs in `status ∈
  {queued, running}` rejects a duplicate concurrent import/retry for the same
  site/provider/window — the operator gets the existing in-flight job, not a second
  pull. (Completed jobs may share a key across replays; only in-flight ones are
  exclusive.)
- Job execution claims the site/provider with a short row-level lock
  (`SELECT … FOR UPDATE` on the account/site row) for the duration of the
  synchronous run, so two admins clicking "Run" cannot double-pull.

**`row_count` / replay semantics (defined explicitly to avoid ambiguity):**
- `rows_attempted` = rows the adapter returned for the window.
- `rows_written` = rows **actually inserted** by this job (post-`ON CONFLICT DO
  NOTHING`); a replay over already-present data therefore reports
  `rows_written = 0` while still succeeding.
- `weather_observation_batches.row_count` keeps its existing meaning (rows persisted
  by the batch that created it) and is **not** re-defined.
- The integrity endpoint (§5.2) reports **recovered coverage** (distinct observation
  timestamps present for the window) separately from any single batch's `row_count`,
  because after a restore + replay the same coverage may be spread across new
  `batch_id`s with `rows_written = 0` on the replay job. "Replay is idempotent on
  observations" is **not** the same as "replay reproduces the original batch lineage."

### 4.4 `weather_provider_accounts` — new columns (nullable; best-effort)
Populated only when the adapter response actually reports them; otherwise stay NULL
and surface as honest **N/A** (never `0`).
- `quota_limit`, `quota_used`, `quota_window_start`,
  `rate_limit_remaining`, `rate_limit_reset_at`,
  `last_provider_status_code`.

> **Decision (recommended):** nullable columns over a separate usage table — the
> account already owns health fields, and free providers (Open-Meteo) report no
> quota, so a rolling-history table would mostly be empty. Revisit only if a paid,
> quota-metered provider is onboarded.

### 4.5 No changes to
`weather_observations`, `weather_sources`, `weather_source_profiles`,
`weather_source_approvals`, `weather_device_mappings`, or anything the resolver
reads. Coverage/gap/trend/metrics are **computed read-only** from existing
batch/job/observation rows — no materialized columns required for MVP.

---

## 5. Required API Additions

All new write endpoints reuse existing guards (`telemetry_admin_required` +
`_enforce_company_visibility` for site/company scope; a **platform-admin** guard for
the global catalog — see §12). All read endpoints are zero-write.

### 5.1 Catalog lifecycle (platform-admin; global catalog)

> **Global-enable vs. company exposure (rollout-critical).** `is_enabled` lives on
> the **global** catalog, so flipping it on potentially lets *every* eligible
> company admin run a **keyless** provider (e.g. Open-Meteo, which needs no account
> and only a licensing ack). A global flag is therefore **not** sufficient for a
> single-company pilot. D.5a must add ONE of: (a) a company-level provider
> **entitlement/allowlist** consulted in `_resolve_provider_pull_context`, or
> (b) require a company-scoped **account + acknowledgment even for keyless
> providers** during pilot. Recommendation: (a) entitlement allowlist — it scopes
> pilot blast-radius without changing the keyless UX long-term. Until that exists,
> treat global-enable as an all-companies action and pilot only in an environment
> with a single company. This is a **rollout blocker**, tracked in §14.

- `POST /providers/{provider_key}/enable` (body: `rationale`) — governed flip →
  audit row.
- `POST /providers/{provider_key}/disable` (body: `rationale`) — **safe disable**:
  blocks new pulls via existing `is_enabled` check; **retains** all batches/
  observations; context + history still render.
- `POST /providers/{provider_key}/approve`
- `POST /providers/{provider_key}/suspend`
- `POST /providers/{provider_key}/retire` (sets archived/retired)
- `POST /providers/{provider_key}/restore`
- `GET  /providers/{provider_key}/audit` — read-only lifecycle ledger.

State machine (enforced server-side; illegal transitions → `409` via
`JSONResponse` so the detail survives the exception handler):
`draft → approved → (enabled ⇄ disabled / suspended) → retired → (restore →
approved)`. Enabling requires `approved`. Retire/suspend force-disable.

### 5.2 Import jobs & admin tooling (site/company-scoped)
- `GET  /sites/{sid}/provider-import/jobs` (read-only history; richer than batches)
- `GET  /sites/{sid}/provider-import/jobs/{job_id}`
- `POST /sites/{sid}/provider-import/jobs/{job_id}/retry` — re-runs the same window
  (idempotent; new job, `parent_job_id` set, `trigger=retry`).
- `POST /sites/{sid}/provider-import/preview` — **EXISTS**; documented as the
  "re-preview window" tool (caller passes the explicit prior window).
- `GET  /sites/{sid}/provider-import/batches/compare?batch_a=&batch_b=` — read-only
  diff (row counts, window/coverage overlap, per-metric/per-timestamp value deltas).
- `GET  /sites/{sid}/provider-import/integrity?batch_id=` — read-only: `row_count`
  vs `COUNT(observations)`, `dedupe_key` uniqueness, request/response hash presence,
  coverage vs requested window.

### 5.3 Monitoring / health
- `GET /companies/{cid}/weather-provider-metrics?window=` — read-only success/
  failure trend, coverage %, gap intervals aggregated across the company's sites.
- `GET /providers/health` — read-only operational rollup: per-provider catalog
  state + version + per-account health summary + last batch outcome.
- `GET /health/weather-providers` — lightweight framework **liveness** (no external
  calls; mirrors `/health`).

> **Account "safe disable"** already exists via
> `PATCH .../accounts/{aid}` with `status=paused|archived` — documented as the
> account-level safe-disable; no new endpoint needed there.

---

## 6. Required UI Additions

### 6.1 Portfolio Admin — `WeatherProviderAdminSection.tsx` (extend)
- Catalog table with lifecycle controls (Enable / Disable / Approve / Suspend /
  Retire / Restore), each gated to platform admin and requiring a **rationale**.
- Columns: `approval_state`, `provider_version`, last-toggle actor/time, account
  health rollup.
- **Lifecycle audit drawer** (read-only ledger from `/providers/{key}/audit`).
- Provider-health summary card (aggregate from `/providers/health`).

### 6.2 Project Hub → Telemetry tab (extend existing components)
- **Import history** view (jobs, not just batches): status, trigger, window,
  rows_written, retry lineage; success/failure trend sparkline; coverage % and gap
  list.
- Per-batch/job actions: **Retry** (failed/partial only), **Re-preview window**
  (opens `ImportExternalWeatherDialog` prefilled), **Compare** with another batch
  (diff view), **Integrity check** (result chips).
- `ExternalWeatherContextPanel` keeps its honest **context-only** banner unchanged.

### 6.3 Operational dashboard (new read-only section under Portfolio Admin)
- Company-wide success/failure trends, coverage metrics, gap metrics; last
  successful/failed pull per account; quota/rate-limit status when reported, else
  **N/A** (never `0`).

### 6.4 Honest-unavailable rule (enforced everywhere)
`null` / `undefined` / `'N/A'` render as a neutral unavailable state — never `0` or
`0%` — mirroring the existing context panel and the O&M device-detail conventions.

---

## 7. Monitoring Design (Focus Area 5)

- **Structured logs**: adopt event names
  `weather_provider_import_started|succeeded|partial|failed`,
  `weather_provider_lifecycle_changed`, `weather_provider_credential_test`,
  `weather_provider_retry`, via `logging.getLogger(__name__)` with key=value
  context (site_id, provider_key, account_id, job_id, window, row counts). No PII,
  no secret values, no credential fingerprints in logs.
- **Metrics**: derived read-only from job/batch tables (counts, success rate,
  coverage, gaps) and exposed via the metrics endpoints — no external metrics
  system required for MVP. If a metrics sink is later adopted, emit the same events.
- **Alerts / failure notifications**: opt-in (default OFF), **inline** via the
  already-configured **Mailgun** — sent at the moment of a failed import or a
  detected credential-`expired`/`invalid` during an operator action. **No
  background poller** (honors the no-scheduler guardrail). Recipients/threshold
  (e.g. N consecutive failures) configured per company by an admin.
  - **Config storage (required if thresholds/recipients are supported):** a small
    additive `weather_provider_notification_pref` row per company (`company_id`,
    `enabled` default `false`, `recipient_emails` `JSONB`, `failure_threshold`
    `INT`, `notify_on_credential_expiry` `BOOL`). If this config table is **not**
    built, the notification feature stays **out of the D.5c MVP** rather than
    shipping with hardcoded recipients — pick one explicitly (see §14).
- **Health endpoints**: `/health/weather-providers` (liveness) and
  `/providers/health` (operational rollup).

---

## 8. Disaster Recovery Design (Focus Area 6)

- **Backup/restore validation**: weather_* tables are covered by standard Postgres
  backups/PITR. Validation runbook = restore to staging → call the integrity
  endpoint per recent batch → confirm `row_count == COUNT(observations)` and
  `dedupe_key` uniqueness.
- **Replay imports**: re-running an import for a window is a **safe no-op** because
  observations are idempotent (`ON CONFLICT DO NOTHING` on `dedupe_key`). Replay is
  recorded as a new job; no data is overwritten or deleted.
- **Duplicate detection**: enforced by `dedupe_key`; the integrity endpoint reports
  any anomaly count (expected zero).
- **Integrity verification**: per-batch `row_count` vs actual observations,
  request/response hash presence, coverage vs requested window.

---

## 9. Testing Plan

Mirror the existing harness conventions (`backend-test-harness` memory): run with
`test_db_name=heliumdb_test python -m pytest <files> -o addopts="" -p no:cacheprovider -q`,
run **files directly** (the full `tests/` dir has 3 pre-existing unrelated
collection errors), use `monkeypatch` (no `pytest-mock`).

- **Unit**: lifecycle state machine (legal transitions + illegal→409); governed
  enable/disable/approve/suspend/retire/restore each writes the correct audit row;
  rollback = reverse entry (history immutable); job status transitions; retry
  lineage (`parent_job_id`); integrity computation; batch compare diff; metrics
  aggregation; default-deny licensing still enforced unchanged.
- **Invariant / golden**: `compute_site_expected_period_effective` **byte-identical**
  (sha256) across every new operation; `WeatherResolver.resolve_window` unchanged;
  observations remain `ghi/ambient/unknown` (no poa/cell introduced);
  `physics_usable_rows == 0`.
- **Integration**: recorded Open-Meteo fixture → import job → batch → integrity →
  retry (no-op) → compare. (Live pull optional; fixture is the CI path.)
- **Negative**: disabled/suspended/retired provider blocks pull; unacknowledged
  restricted licensing blocks; durability gate fires in prod-like env names;
  non-admin blocked from catalog lifecycle endpoints; safe-disable retains data.

---

## 10. Browser Validation Plan

Phase D could not do browser validation (no auth session). D.5 explicitly plans for
it. **Dependency to flag: a test admin session / credentials are required** — if
unavailable, fall back to the service-layer harness pattern proven in Phase D.

Steps (capture screenshots + network responses + a before/after expected chart):
1. Portfolio Admin → approve + enable Open-Meteo for a pilot company → verify the
   lifecycle audit drawer shows the entries.
2. Project Hub → pilot site (non-protected, e.g. site 18) → Telemetry → Import
   dialog → **preview** a window → **run** import → see the job in history with
   `succeeded` + coverage.
3. Induce a failure (e.g. impossible window) → see `partial`/`failed` → **Retry** →
   confirm idempotent success.
4. **Compare** two batches; run **Integrity** check (passes).
5. Confirm `ExternalWeatherContextPanel` still shows the **context-only** banner and
   the expected/actual charts are visually unchanged.
6. **Safe-disable** the provider → confirm new imports are blocked but context +
   history still render (no data loss).

---

## 11. Migration Readiness (Focus Area 7)

- **Single additive migration** chaining from the current head. The Alembic tree is
  **branched** (multiple leaf heads observed), so run `alembic heads` first; if more
  than one head exists, author an `alembic merge` migration before/with the D.5
  revision so `alembic upgrade head` is unambiguous.
- All new columns are **nullable or server-defaulted**; new tables are independent.
  **Forward + downgrade both tested** — downgrade cleanly drops the nullable columns
  and the new tables (no data dependency in the resolver/expected path).
- **Pre-migration catalog-state audit (required).** Because `approval_state`
  defaults to `draft` while some rows may already have `is_enabled=true`, the
  migration would otherwise leave "enabled-but-not-approved" rows that violate the
  new "enable requires approved" rule. Before/within the migration, audit every
  catalog row and apply a **deterministic** decision: any row currently
  `is_enabled=true` is backfilled to `approval_state='approved'` (it was already in
  use), and rows `is_enabled=false` stay `draft`. (In dev today Open-Meteo is
  `is_enabled=false`, so the audit is a no-op there — but production must be checked,
  not assumed.) Record the decision per row in `weather_provider_catalog_audit` with
  a `migration_backfill` rationale so the state transition is itself auditable.
- **No behavior-changing backfill.** An optional idempotent backfill may set the new
  `approval_state` to `approved` for the already-seeded Open-Meteo row **only**, and
  must:
  - fill **only NULL** operational columns (never overwrite operator values),
  - **fingerprint protected-site (site 4 / 110 Shawmut) telemetry mappings before &
    after**, aborting + rolling back on any add/remove/edit (mirror the
    `device_classification` backfill guard),
  - never touch observations, batches, or mappings.

---

## 12. Rollout, Rollback, Smoke Tests, Runbooks (Focus Area 7)

### 12.1 Rollout sequencing
1. Apply migration (providers stay `is_enabled=false`, `approval_state=draft`).
2. Deploy backend (lifecycle/job/metrics endpoints live but inert until a provider
   is approved+enabled).
3. Deploy FE (admin lifecycle controls + monitoring).
4. Platform admin **approves + enables** one provider for one pilot company on a
   **non-protected** site.
5. Run a manual import → verify context-only + charts byte-identical + integrity OK.
6. Widen to more companies/sites.

### 12.2 Rollback plan
The feature is additive and default-off, so rollback is graduated and **never loses
data**:
- **Instant**: `POST /providers/{key}/disable` (blocks new pulls; retains all data).
- **Deploy revert**: roll back FE/backend; existing batches/observations remain
  readable.
- **Schema**: `alembic downgrade` drops the nullable columns + new tables cleanly.
- At every step the resolver/expected/baseline path is untouched.

### 12.3 Smoke tests (post-deploy)
enable→disable cycle writes audit; account create honors licensing gate; preview a
window; import a window then re-run (idempotent no-op); retry a failed job;
integrity check passes; context-only invariant holds; expected chart byte-identical.

### 12.4 Operational runbooks (to author)
- Approve + enable a provider (and the reverse: safe-disable / retire).
- Rotate credentials (durability gate behavior in prod-like envs).
- Investigate a failed import (logs → job → batch → integrity → retry).
- Replay a window after data loss (idempotent).
- Respond to credential expiry (notification → re-test → rotate).
- Verify integrity after a restore.

---

## 13. Invariant Preservation Matrix

| Invariant (A–D) | How D.5 preserves it | Proof |
|---|---|---|
| `WeatherResolver` unchanged | D.5 adds only lifecycle/job/metrics; never edits resolver or its source selection | Golden test: `resolve_window` before==after |
| Expected math unchanged | No new code path feeds expected; metrics read batches/jobs only | `compute_site_expected_period_effective` sha256 byte-identical |
| Baselines unchanged | No baseline read/write added | Baseline read verbatim; no baseline endpoint touched |
| No GHI→POA / ambient→cell | No conversion code added; observations keep declared planes/types | Integrity/context assert `ghi/ambient/unknown`, no poa/cell |
| Context-only | New ops never set physics-usable semantics | `physics_usable_rows == 0`; context banner unchanged |
| No scheduler | Jobs run synchronously; notifications inline; no poller/lease | No `scheduled` trigger; no `TelemetrySchedulerState` analog |
| Default-deny licensing | Lifecycle endpoints don't bypass `_resolve_provider_pull_context` | Negative test: unack restricted still 422 |
| Durability gate | Reused unchanged on any credential-touching path | Negative test in prod-like env names |
| `Site` entity unchanged | All additions are weather_* tables/columns | No migration touches `sites` |
| Protected site 4 / 110 Shawmut | Backfill fingerprints + aborts on any mapping change | Before/after fingerprint equality |

---

## 14. Open Decisions (require sign-off before D.5a build)

1. **Catalog lifecycle authorization scope.** The catalog is **global**, so
   enable/approve/retire should require a **platform/super-admin** role, not a
   company-scoped `telemetry_admin`. Confirm the correct existing role/permission
   (or decide to introduce one). *This is the single biggest unknown.*
2. **Blank/None licensing posture** (carried from Phase D): currently treated as
   unrestricted. Product/legal decision whether to make blank fail-closed.
3. **Failure notifications** via Mailgun: confirm opt-in + inline-only (no poller)
   is acceptable, and the default threshold.
4. **Job table vs. extending batches**: recommendation is a **separate**
   `weather_provider_import_job` table (keeps batches immutable). Confirm.
5. **Quota/rate-limit**: recommendation is **nullable account columns** over a
   usage-history table. Confirm.
6. **Operational dashboard placement**: new section under Portfolio Admin vs. a
   dedicated route. Recommendation: section under Portfolio Admin to avoid new
   top-level navigation.
7. **Keyless-provider company scoping (rollout blocker, see §5.1)**: global
   `is_enabled` would expose keyless providers to all eligible companies at once.
   Decide between a company-level **entitlement allowlist** (recommended) vs.
   requiring a company-scoped account+ack even for keyless providers during pilot.
   Must be resolved before D.5a enables any provider in a multi-company environment.
8. **Notification config**: build `weather_provider_notification_pref` (per-company
   recipients/threshold) in D.5c, or keep failure notifications out of the MVP. No
   hardcoded recipients.

---

## 15. Explicit Non-Goals (D.5 will NOT do)

- No physics use of external weather (Phase E) — no GHI→POA, no ambient→cell.
- No scheduler / automated pulls / background pollers.
- No changes to `WeatherResolver`, expected math, baselines, or the `Site` entity.
- No paid-provider commitment or new external provider onboarding.
- No new secrets beyond the existing GCP Secret Manager credential model.
- No WS.5 / device-semantics changes.
