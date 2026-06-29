# Production Rollout Checklist — Weather Provider Framework

> **Architecture freeze (D.6). Documentation only.** Ordered, gated rollout with a
> graduated, no-data-loss rollback. Assumes D.5a (lifecycle/job/entitlement) is built
> and reviewed; steps that depend on D.5a are tagged **[D.5a]**.

## Pre-flight (must all be true before starting)

- [ ] All frozen invariants verified by tests (ADR-0001…0006): expected math
      byte-identical; resolver unchanged; observations `ghi/ambient/unknown`;
      `physics_usable_rows = 0`.
- [ ] Default-deny licensing gate green (unack restricted → blocked).
- [ ] Durability gate verified for the target prod-like environment name
      (`production`/`prod`/`staging`/`stage`/`live`).
- [ ] **[D.5a]** Platform-admin authorization enforced on catalog lifecycle
      endpoints (NOT company telemetry_admin).
- [ ] **[D.5a]** Company **entitlement** decision made — global `is_enabled` would
      otherwise expose a keyless provider to all companies.
- [ ] Durable credential store (GCP Secret Manager) configured for keyed providers.
- [ ] Backup/restore + replay validated in staging (DR guide).
- [ ] Runbooks reviewed by the operating team.

## Migration readiness

- [ ] Run `alembic heads`; if multiple heads, author a merge migration so
      `alembic upgrade head` is unambiguous (tree is branched).
- [ ] New columns nullable/defaulted; new tables independent.
- [ ] **Pre-migration catalog-state audit:** any row `is_enabled=true` is backfilled
      to `approval_state='approved'`; `is_enabled=false` stays `draft`. Record each in
      `weather_provider_catalog_audit` with `migration_backfill` rationale.
- [ ] Optional backfill fills **only NULL** operational columns; **fingerprints the
      protected site (4 / 110 Shawmut) telemetry mappings before & after**, aborting +
      rolling back on any add/remove/edit.
- [ ] Forward **and** downgrade tested.

## Rollout sequence (ordered)

1. [ ] Apply migration (providers remain `is_enabled=false`, `approval_state=draft`).
2. [ ] Deploy backend (lifecycle/job/metrics endpoints live but inert until a
       provider is approved+enabled).
3. [ ] Deploy frontend (admin lifecycle controls + monitoring).
4. [ ] **[D.5a]** Platform-admin **approves + enables** ONE provider for ONE pilot
       company (entitlement) on a **non-protected** site.
5. [ ] Run **preview** then **import** a small window; verify context-only + charts
       byte-identical + integrity OK.
6. [ ] Observe for the agreed soak period (logs, metrics, no expected-math drift).
7. [ ] Widen to additional companies/sites incrementally.

## Smoke tests (post-deploy)

- [ ] enable→disable cycle writes audit rows (reverse entries).
- [ ] account create honors licensing gate (unack restricted → 422).
- [ ] preview writes nothing; import writes a batch.
- [ ] re-import same window → idempotent (`rows_written = 0`, still succeeds).
- [ ] retry a failed job → succeeds; lineage recorded.
- [ ] integrity check passes (row_count vs observations; recovered coverage).
- [ ] context-only invariant holds; expected chart byte-identical.

## Rollback plan (graduated; never loses data)

1. [ ] **Instant:** `disable` the provider (blocks new pulls; retains all data).
2. [ ] **Deploy revert:** roll back FE/backend; existing data stays readable.
3. [ ] **Schema:** `alembic downgrade` drops nullable columns + new tables cleanly.
4. [ ] Confirm resolver/expected/baseline path untouched at every step.

## Sign-off

- [ ] Engineering: invariants + migrations verified.
- [ ] Platform-admin/Operations: runbooks + DR rehearsed.
- [ ] Product/Legal: licensing posture (incl. blank/None class) decided.
- [ ] Reviewer: confirmed this rollout introduces **no** Phase E / physics behavior.
