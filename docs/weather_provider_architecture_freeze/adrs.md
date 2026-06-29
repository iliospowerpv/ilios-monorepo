# Architecture Decision Records — Weather Provider Framework

> **Architecture freeze (Phase D.6). Planning/documentation only — no code change.**
> ADRs use a standard format: **Context → Decision → Status → Consequences →
> Enforcement / How we'd know it broke**. "Status" includes a build tag
> (**[BUILT]** / **[DESIGNED]** / **[FUTURE]**) per the package README.

---

## ADR-0001 — External weather remains context-only

**Status:** Accepted — **[BUILT]** (Phases A–D).

**Context.**
The platform's expected-energy and baseline math is physics-grade: it consumes
plane-of-array irradiance (POA, W/m²) and module **cell** temperature. Most
affordable/free external weather providers (Open-Meteo, NOAA, Meteostat, etc.) emit
**global horizontal irradiance (GHI)** and **ambient** air temperature. Converting
GHI→POA or ambient→cell is a modeling act with material accuracy and liability
implications. Phase D delivered the ability to pull external weather, but the value
of that data without the modeling layer is **provenance, context, readiness signals,
and cosmetic display** — not physics.

**Decision.**
External weather is stored, audited, and displayed as **context only**. Every
external observation is persisted with its true, declared semantics
(`irradiance_plane`, `temperature_type`), defaulting to `unknown` when the provider
does not state plane/height. Such rows are **never** counted as physics-usable and
**never** flow into expected/baseline computation. The site context endpoint reports
`physics_usable_rows == 0` and an explicit "context only — not expected-eligible"
banner.

**Consequences.**
- (+) The platform can show external weather coverage, gaps, and provenance without
  risking expected-energy accuracy or implying a physics guarantee it cannot back.
- (+) Onboarding a new free provider is safe by construction.
- (−) External weather cannot improve expected math today; that is deferred to a
  separately reviewed Phase E with a real transposition model.

**Enforcement / how we'd know it broke.**
The resolver's POA-only / cell-only test (ADR-0002, ADR-0004) is the structural gate.
Golden tests assert `compute_site_expected_period_effective` is **byte-identical**
before vs after any external import, and that imported observations remain
`ghi/ambient/unknown` with `physics_usable_rows == 0`.

---

## ADR-0002 — `WeatherResolver` immutability (in this track)

**Status:** Accepted — **[BUILT]** (frozen).

**Context.**
`WeatherResolver.resolve_window` is the single seam that decides which weather a site
uses for physics, and applies the POA-only / cell-only acceptance test before any
value reaches `compute_expected_buckets`. It is the chokepoint that makes ADR-0001
true. Any change to it risks silently widening what counts as physics-usable.

**Decision.**
The resolver is **immutable** for the entire weather-provider track (Phases A–D, D.5,
D.6). New provider/governance/observability work routes **around** it (it never reads
the new job/lifecycle/metrics tables) and never edits its source-selection or
acceptance logic. The resolver continues to select only governed POA/cell sources —
either DAS streams (W1) or, where built, an **approved POA/cell historical profile**
(W2). Third-party provider context pulls are `ghi/ambient/unknown`, so they are neither
that semantics nor an approved POA/cell source, and the resolver does not select them.

> **Accuracy note (freeze):** "immutable in this track" means the provider framework
> does not change the resolver. It does **not** mean the resolver is blind to all of
> `weather_observations` — the built W2 path can read *approved POA/cell* observations.
> The invariant that holds is narrower and exact: **provider GHI/ambient pulls are
> never selected for physics**, enforced by the POA-only/cell-only test (ADR-0004).

**Consequences.**
- (+) The physics boundary has exactly one well-tested gate, not many.
- (+) Reviewers can reason about Phase E by reasoning about this one function.
- (−) Any legitimate future need to consume external weather for physics **must** be
  an explicit, separately reviewed change to this function — by design, not by
  accident.

**Enforcement / how we'd know it broke.**
Golden test: `WeatherResolver.resolve_window` output is identical before vs after any
provider-framework change for the same inputs (status, source_type, selected
`weather_source_id`). Code review treats any diff to the resolver in a
provider-framework PR as a blocking violation.

---

## ADR-0003 — Job vs. Batch separation

**Status:** Accepted — **[DESIGNED]** (D.5a; not yet built).

**Context.**
`weather_observation_batches` is **immutable provenance**: one row per successful/
partial/failed pull, carrying request/response hashes, provider API version, and a
row count. Operational governance needs richer, mutable lifecycle: `queued`/`running`
states, retry lineage, idempotency keys, and per-attempt error history. Overloading
the immutable provenance table with mutable attempt state would corrupt the audit
trail.

**Decision.**
Track import **attempts** in a separate `weather_provider_import_job` table (mirroring
`TelemetrySyncJob`) with `status`, `trigger ∈ {manual, retry, re_preview}` (no
`scheduled`), `parent_job_id` (retry lineage), `idempotency_key`, and row
`attempted`/`written` counts. A job *references* the batch it produced
(`batch_id`); the batch itself is never mutated to express attempt state.

**Consequences.**
- (+) Provenance stays immutable and audit-grade; lifecycle stays expressive.
- (+) Retry/replay history is first-class without polluting batches.
- (−) Two tables to reason about; metrics must join job + batch.

**Enforcement / how we'd know it broke.**
Batches have no `updated_at` and no lifecycle/`trigger` columns. A partial unique
index on `idempotency_key` for in-flight jobs prevents duplicate concurrent pulls.
Any migration adding mutable lifecycle columns to `weather_observation_batches` is a
violation.

---

## ADR-0004 — GHI is never POA (and ambient is never cell)

**Status:** Accepted — **[BUILT]** (frozen; the strictest form of ADR-0001).

**Context.**
The most dangerous silent failure mode is treating horizontal irradiance as
plane-of-array, or ambient air temperature as module cell temperature. Both would
make expected energy look plausibly wrong. Providers frequently omit plane/height
metadata, tempting an "assume POA" shortcut.

**Decision.**
No transposition or conversion exists anywhere in the framework. Unknown semantics
stay `unknown` — they are never promoted to `poa`/`cell`. The metric catalog and
import path declare what the provider said; they never infer what it "must mean." A
governed reviewer declaration (the existing weather-device-mapping declaration flow)
is the **only** path that can ever assert physics-usable semantics, and even that
does not perform conversion.

**Consequences.**
- (+) Expected energy can never be silently corrupted by mislabeled inputs.
- (−) GHI-only providers are permanently context-only until a Phase E transposition
  model (with its own validation) is built and reviewed.

**Enforcement / how we'd know it broke.**
Tests assert no code path writes `irradiance_plane='poa'` or
`temperature_type='cell'` from GHI/ambient inputs. The integrity/context endpoints
report the distribution of planes/types; a `poa`/`cell` row appearing from an
external `provider_pull` batch is a red-flag anomaly.

---

## ADR-0005 — Replay / idempotency semantics

**Status:** Accepted — **[BUILT]** (observation idempotency) + **[DESIGNED]** (job-level replay).

**Context.**
Re-importing a window must be safe (for DR replay, retries, and accidental double
clicks), but operators must not be misled into thinking "replay = exact
reconstruction."

**Decision.**
Observations are idempotent on a unique `dedupe_key` via `INSERT … ON CONFLICT DO
NOTHING`, so re-importing a window inserts zero duplicate rows. **However**, replay is
explicitly **not** a reproduction of the original batch lineage: a replay creates a
**new** job and (if it writes anything) a **new** batch, and reports
`rows_written = 0` when the data was already present. Integrity reporting therefore
distinguishes **recovered coverage** (distinct observation timestamps present for a
window) from any single batch's `row_count`.

**Consequences.**
- (+) Replays and retries are safe and never duplicate data.
- (+) Operators get an honest picture: "the data is there" is separate from "this
  batch produced N rows."
- (−) After a restore, coverage may be spread across new batch IDs; tooling must
  reason about coverage, not batch identity.

**Enforcement / how we'd know it broke.**
The `dedupe_key` unique constraint (**[BUILT]**). An integrity endpoint
(**[DESIGNED]**, D.5a) that reports `row_count == COUNT(observations)` per batch **and**
total recovered coverage for a window; until it ships, the same checks run via the
built batches endpoint plus read-only SQL on `weather_observations` /
`weather_observation_batches`. A replay that produced duplicate observation rows would
be a `dedupe_key` constraint violation.

---

## ADR-0006 — Provider governance model

**Status:** Accepted — **[BUILT]** (licensing + durability gates, default-off catalog) + **[DESIGNED]** (lifecycle state machine, audit ledger, entitlement).

**Context.**
External providers carry licensing, credential-durability, blast-radius, and
auditability risks. A "just flip it on" model is unsafe for a multi-company platform.

**Decision.**
Governance is layered and explicit:
- **Default-off catalog.** `weather_provider_catalog.is_enabled` defaults `false`.
- **Default-deny licensing.** Only an explicit unrestricted allowlist is exempt;
  every other class (incl. `free_noncommercial`, unknown/future strings) requires an
  acknowledged per-company account before any pull. `catalog.licensing_class` takes
  precedence over `capabilities_json`.
- **Durability gate.** In prod-like environments (`production`/`prod`/`staging`/
  `stage`/`live`), credential-touching operations are blocked unless the credential
  store is durable (GCP Secret Manager); the DB stores only `secret_name`, never the
  secret.
- **[DESIGNED] Lifecycle state machine** (`draft → approved → enabled ⇄ disabled /
  suspended → retired → restore`) under a **platform-admin** guard (the catalog is
  global), with an **append-only** audit ledger where rollback = a reverse entry.
- **[DESIGNED] Company entitlement** so a globally-enabled keyless provider does not
  expose every company at once.

> **Accuracy note (freeze):** the **currently built** pull gate
> (`_require_catalog_provider`, consulted by preview/import via
> `_resolve_provider_pull_context`) checks **only `is_enabled`** — plus the built
> licensing-ack and durability gates. Approval state, the lifecycle state machine,
> the catalog audit ledger, and company entitlement are all **[DESIGNED]** (D.5a) and
> are **not** enforced by code today.

**Consequences.**
- (+) Enabling a provider is a deliberate, audited, reversible act with the right
  authorization scope.
- (−) More moving parts; lifecycle/entitlement are still to be built (D.5a).

**Enforcement / how we'd know it broke.**
Negative tests: unacknowledged restricted licensing → blocked; prod-like env +
non-durable store → blocked; non-platform-admin → blocked from lifecycle endpoints.
The append-only audit ledger must never be mutated/deleted.

---

## Cross-cutting non-decisions (explicitly deferred to Phase E or later)

These are **not** decided here and must be made under separate review:

- Whether/how to perform GHI→POA transposition or ambient→cell modeling
  (the core of Phase E — see `phase_e_readiness_assessment.md`).
- Whether to onboard any paid/commercial provider.
- Whether to add scheduler automation for pulls (explicitly excluded in D.5/D.6).
- The blank/None licensing-class posture (currently treated as unrestricted) —
  a product/legal decision carried forward from Phase D.
