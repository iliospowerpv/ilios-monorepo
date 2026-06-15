---
name: weather provenance foundation (W0)
description: Design contract of the native weather domain that coexists beside V2 telemetry; what W1 must still decide.
---

# Weather Data Architecture W0 — native weather provenance

W0 is a **schema/model/CRUD foundation only**, deliberately ADDITIVE — it adds a
native PostgreSQL weather domain (sources, effective-dated source profiles,
import batches, observations, an approval ledger, device→semantics mappings, and
an `expected_weather_provenance` table) and changes **no** runtime behavior in
`expected_service`, telemetry ingestion, O&M charts, scheduler, DD, baselines, or
reconciliation. It **coexists beside `telemetry_readings`** and never replaces it.

## Durable contracts (don't violate in W1+)

- **Never guess measurement semantics.** `irradiance_plane`, `temperature_type`,
  `confidence`, `calibration_status` all default to `unknown`. There is NO
  GHI/DNI/DHI→POA and NO ambient→cell conversion anywhere — unmapped DAS weather
  stays `unknown`, never assumed POA/cell.
  **Why:** the whole point of the provenance layer is honesty about what a number
  physically is; a silent conversion would defeat it.
- **Profiles are versioned by NEW ROW, never auto-activated** (status default
  `draft`), and **overlapping active profiles per (site, role) are allowed on
  purpose** — there is intentionally NO single-active partial-unique constraint.
  Precedence is expressed by `priority` (+ effective window), to be resolved by a
  future W1 resolver.
  **Why:** the resolver needs room to express precedence/fallback; a single-active
  DB constraint would foreclose that.
- **Observations are append-only / idempotent on `dedupe_key`** (`INSERT … ON
  CONFLICT DO NOTHING`); existing rows are never updated/deleted. The approval
  ledger and "version-by-new-row" are **contracts, not DB-enforced** — do NOT
  expose generic update/delete endpoints for these tables without an explicit
  policy.
- **`expected_weather_provenance` is defined but NOT written by any runtime in
  W0.** Keep runtime writes deferred until the resolver is explicitly designed.

## What W1 (resolver) still has to decide

- Deterministic tie-break for equal `priority`.
- Effective-window boundary inclusivity (`effective_from`/`effective_to`).
- Source-scope precedence: CRUD `list_for_site` is site-scoped only; if company-
  or global-scoped sources are intended, the resolver must fold them in.
- Profile `status` filter (which statuses are eligible for selection).
