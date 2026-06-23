---
name: Weather semantics governed declaration (Layer-1)
description: Governed draft→active→superseded lifecycle over weather_device_mappings — single-active concurrency, append-only guard, never-infer semantics, immutable upstream fingerprint + stale re-review.
---

# Weather semantics governed declaration (Layer-1)

Additive governance layer over `weather_device_mappings`. Records what a device's
weather stream *means* (irradiance plane / temperature type / calibration) as a
versioned, auditable declaration. **Layer-1 only**: never touches WeatherResolver
math, expected formula, ingestion, rollups, scheduler, device
eligibility/classification, baselines, or O&M. Never writes
`expected_weather_provenance`.

## Core rules (durable)
- **Semantics are never inferred.** Plane/temperature/calibration default to
  `unknown`; only an explicit declaration sets POA/cell/etc. No conversion (GHI is
  not transposed to POA).
- **Correction = NEW row + explicit supersession**, never an in-place edit of a
  governed row.
- **`needs_re_review` is a BOOLEAN flag (+`re_review_reason`), NOT a status.** It is
  monotonic, never auto-cleared; it clears only when a NEW activated declaration
  supersedes the row.
- Two layers cooperate: a **BEFORE UPDATE trigger** (the declaration guard) enforces
  the *shape* of an UPDATE (which columns may change) on governed rows only — legacy
  NULL-status rows are exempt; the **declaration service** enforces the *policy*
  (evidence completeness, cross-tenant resolvability, single-active, supersession)
  and writes the immutable `weather_source_approvals` ledger. Service commits exactly
  once; ledger helper only add/flush so multi-step ops are atomic.

## Single-active concurrency (the non-obvious part)
**Why:** a `SELECT … FOR UPDATE` on existing active rows cannot serialize two
concurrent activations of an *empty* lineage — both observe zero active rows and
both proceed, yielding two active rows.
**How it's solved:** two PARTIAL UNIQUE indexes are the durable DB backstop — one on
`(site_id, device_id, metric)` for device-keyed rows, one on
`(site_id, external_device_id, metric)` for external-keyed rows, each
`WHERE declaration_status='active'`. PARTIAL so legacy(NULL)/draft/superseded rows
are never constrained — only the one live row per lineage. Consequences:
- The index is **non-deferrable (per-statement)**, so activation must **supersede the
  prior active row FIRST (flush) THEN flip the new draft to active (flush)** — the
  lineage never holds two active rows at any flush point.
- `IntegrityError`→409 must be **narrowed to those two constraint names** (via
  `exc.orig.diag.constraint_name`); a blanket map would mislabel unrelated FK/NOT NULL
  faults as a "concurrent activation".
- Caveat: PG treats NULLs as distinct, so the external index does not constrain rows
  where BOTH device_id and external_device_id are NULL. Moot while declare requires
  `device_id`; revisit if external-only declarations are added.

## Evidence revalidation
Cross-tenant evidence (`source_document_id`/`source_file_id` must resolve to THIS
site) is validated at BOTH create AND activation (inside the activation lock, after
the draft-status check, before completeness) — a draft can be activated long after
its document was re-parented/removed.

## Upstream fingerprint & stale re-review (the detector)
**Decision:** the upstream fingerprint (device-derived inputs that justify the
declared semantics) is captured **only at declaration create/INSERT** and is
**guard-protected (immutable) on governed rows**; the draft snapshot carries forward
to active. Divergence = stored declaration-time fingerprint vs the *live*
device-derived fingerprint.
**Why:** if the fingerprint were recomputed/overwritten later it could never detect
that the upstream device changed underneath an existing declaration — the whole point
of the stale signal.
**How to apply:** the detector is split into a read-only `detect_site` (no
writes/commits, used for preview + diagnostics) and an idempotent `apply_re_review`
(flags only rows that are BOTH diverged AND currently unflagged & active; writes only
`needs_re_review=True` + `re_review_reason` + one `needs_re_review` ledger row; single
commit; `SELECT … FOR UPDATE` on active rows). Preview/apply consistency hinges on
passing the pre-mutation `already_flagged` state explicitly into the divergence DTO
(`would_flag` = pre-state, `needs_re_review` = final state).

## Reconciliation consumer (the reviewer-facing read model)
The reviewer UI does not re-derive verdicts. A strictly read-only
`semantics_reconciliation_service` places every weather-source-capable device into a
9-state taxonomy — the declaration-axis states (from `declaration_policy`); for
*undeclared* semantics the headline splits on whether the device is OBSERVED
(telemetry-mapped via `device.telemetry_mapping` and/or has a `TelemetryReading`):
an observed device is the dedicated state 1
`observed_weather_device_no_governed_declaration` (gap = governance, "review
evidence & declare"), an unobserved device takes the source-axis overlay (states
7–9: `weather_source_missing`/`_stale`/`coverage_incomplete`, where
`weather_source_missing` = nothing observed/mapped AND no source) — plus deduped
site-level counts. Zero writes/commits (`_device_is_observed` is a relationship read
+ bounded `EXISTS`). The frontend renders `state_label`, `state_explanation`,
`required_action`, and `blocking_level` verbatim; never compute the state
client-side or the two surfaces drift.
**Why:** mirrors the inventory-reconciliation pattern — one backend source of truth
for "what position is this in the provenance/governance chain", many read-only views.
Observation is NOT a declaration: an observed device still reports semantics
`unknown` and `expected_model_eligible=False` (never inferred).

## Datetime gotcha (cost a 500 on every call)
A Pydantic `datetime` response field must be populated from a real Python value
(`datetime.utcnow()` / a naive-UTC helper), NOT from a SQLAlchemy `utcnow`
*expression* (the column-default clause). Assigning the SQLAlchemy expression yields a
non-serializable object and Pydantic raises on serialization → 500 on every request,
not just at write time. Caught only at endpoint runtime, not import/unit time.

## Test-harness gotchas (each cost a reset)
- The pytest harness builds schema with `Base.metadata.create_all` (not migrations)
  and the test DB persists between runs. **`create_all` will NOT add a new index to a
  table that already exists** — after adding the partial unique indexes you must reset
  the test DB (`drop_all`) or the new index silently won't exist and the
  single-active DB-invariant test passes vacuously / fails confusingly.
- **Interrupted (timeout-killed) pytest runs leave orphaned locks** on the test DB.
  The guard's CREATE/DROP TRIGGER DDL takes ACCESS EXCLUSIVE and the detector tests
  take `FOR UPDATE`; a killed run can leave a backend idle-in-transaction holding
  those, so the *next* full-file run appears to hang on lock-wait even though every
  test passes individually. It is **not a code deadlock** — diagnose by polling
  `pg_blocking_pids()` / `pg_stat_activity` on the test DB (connect with the
  `DATABASE_URL` creds, swap dbname to the test DB); the fix is to let the orphaned
  connection clear (or terminate it) and re-run, not to change the code.
