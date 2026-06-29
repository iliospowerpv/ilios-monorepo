# Disaster Recovery Guide — Weather Provider Framework

> **Architecture freeze (D.6). Documentation only.** Covers backup/restore
> validation, replay, duplicate detection, and integrity verification for the weather
> provider data. The central safety property is **observation idempotency**
> (`dedupe_key` + `ON CONFLICT DO NOTHING`), which makes recovery actions safe to
> repeat. See ADR-0005 for the precise semantics.

> **Tooling note (build status).** The **integrity endpoint**
> (`GET .../provider-import/integrity`) and the **import-job/retry** endpoints
> referenced below are **[DESIGNED]** (D.5a) and **not built yet**. Until they ship,
> perform the same verification with the **built** batches endpoint
> (`GET .../provider-import/batches`) plus read-only SQL on `weather_observations` /
> `weather_observation_batches`. Replay/recovery itself is fully available today via
> the built, idempotent `provider-import` endpoint.

## 1. What must survive a disaster

| Data | Table | Recovery property |
|---|---|---|
| Measurements | `weather_observations` | Idempotent on `dedupe_key`; replay-safe. |
| Pull provenance | `weather_observation_batches` | Immutable; restored from backup. |
| Attempt history [DESIGNED] | `weather_provider_import_job` | Rebuildable; not physics-critical. |
| Governance state | catalog + `*_audit` + `weather_source_*` | Append-only ledgers restored from backup. |
| Credentials | GCP Secret Manager (NOT the DB) | Recovered via the secret store; DB holds only `secret_name`. |

> Nothing in the resolver/expected/baseline path depends on this data (ADR-0001/0002),
> so a weather-provider data loss can **never** corrupt expected energy — it only
> reduces external **context** coverage until replayed.

## 2. Backup / restore validation (rehearse in staging)

1. Restore the database backup (and confirm GCP Secret Manager access for keyed
   providers) into staging.
2. For several recent batches, run the integrity check (**[DESIGNED]** endpoint, or
   today via the batches endpoint + read-only SQL) and confirm:
   - `row_count == COUNT(observations)` for the batch,
   - `dedupe_key` uniqueness holds (zero duplicates),
   - request/response hash present,
   - recovered **coverage** for the window matches expectation.
3. Confirm the resolver/expected output is **byte-identical** to pre-restore for a
   sample site (it should be — it does not read this data).

## 3. Replay procedure (recover missing coverage)

**When:** a gap in external coverage after an incident.
1. Identify the affected site + window (use coverage/gap metrics).
2. Run **import** for that window (runbooks §3). Idempotency guarantees:
   - already-present rows are **not** duplicated (`rows_written` reflects only true
     new rows),
   - a brand-new job/batch is created (ADR-0005: replay ≠ original lineage).
3. Re-run the integrity check; confirm recovered coverage.

> **Key caveat (ADR-0005):** "replay is idempotent on observations" is **not**
> "replay reproduces the original batch IDs." After a restore + replay, the same
> coverage may be spread across new `batch_id`s with `rows_written = 0` on the replay
> job. Always reason about **coverage**, not batch identity.

## 4. Duplicate detection

- Duplicates are prevented at write time by the `dedupe_key` unique constraint.
- The integrity endpoint reports any anomaly count (**expected: zero**).
- If a non-zero duplicate count ever appears, treat it as a schema/constraint
  regression and escalate to engineering — it implies the unique constraint was lost.

## 5. Integrity verification (routine + post-restore)

For a batch or window, verify:
- [ ] `row_count` (batch) consistent with `COUNT(observations)` linked to it.
- [ ] No duplicate `dedupe_key`.
- [ ] Provider request/response hashes present (provenance intact).
- [ ] Declared semantics still `ghi/ambient/unknown` — **no** `poa`/`cell` from an
      external `provider_pull` batch (ADR-0004). A `poa`/`cell` external row is a
      red-flag anomaly → escalate.
- [ ] Recovered coverage matches the requested window (gaps explainable).

## 6. Credential recovery

- DB stores only `secret_name`; secret **values** live in GCP Secret Manager.
- After DR, confirm the credential store is reachable and durable (durability gate
  will otherwise block credential ops in prod-like envs).
- Re-run account `test`; rotate (runbooks §6) if `credential_status` is
  `invalid`/`expired`.

## 7. What DR does NOT need to do

- No need to recover/replay into the physics path — external weather is never there.
- No scheduler/automation to restart (there is none).
- No reconstruction of exact batch lineage — coverage is the recovery target.
