# Technical Debt Register

A running record of known, accepted technical-debt items: defects or rough edges
that are real but deliberately deferred because they do not block the work in
flight. Each entry should state the symptom, the root cause, what it does and does
*not* affect, and a suggested remediation so a future maintainer can pick it up
with full context.

---

## TD-001 — `alembic upgrade head` from an empty database fails (~`ff19`)

- **Status**: Open / accepted (deferred)
- **Severity**: Low for production; Medium for local dev & CI onboarding
- **Area**: Backend — Alembic migration chain (`backend/ilios-server/alembic`)

### Symptom
Running a clean, from-scratch migration replay against a brand-new, empty
database fails partway through the chain:

```
alembic upgrade head        # from base, empty DB
# ... fails around revision ff19 with, e.g.:
# psycopg2.errors.UndefinedColumn: column users.is_global_admin does not exist
```

The incremental upgrade path that real deployments actually take (applying only
the *new* revisions on top of an already-migrated database) is **not** affected —
this is purely a full-replay-from-base problem.

### Root cause
An early **data** migration executes a live SQLAlchemy ORM query against the
`User` model (rather than a frozen, columns-pinned Core/`text()` statement). The
ORM `User` mapper reflects the *current* model definition, which includes columns
(e.g. `users.is_global_admin`) that are only added by a **later** revision in the
chain. When the data migration runs at its historical point in the sequence those
columns do not yet exist in the database, so the emitted `SELECT` references a
column that is not present yet and Postgres raises `UndefinedColumn`.

In short: a historical migration is coupled to the *latest* ORM schema instead of
the schema as it existed at that migration's point in time. Migrations should be
self-contained and reference only the schema shape valid at their own revision.

### Impact
- **Does NOT affect**: production / staging deploys (they apply incremental
  revisions onto an already-populated schema, never a from-base replay), nor the
  pytest suite (the test harness builds the schema via
  `Base.metadata.create_all`, not via Alembic replay — see
  `tests/conftest.py`).
- **Does affect**: anyone trying to materialize the full schema by replaying
  migrations from an empty DB — fresh local environments that prefer
  `alembic upgrade head` over `create_all`, disposable CI databases built by
  migration replay, and any future migration-correctness/round-trip testing.

### Why it is deferred (not blocking)
This defect is independent of and does **not** block the O&M Weather /
Performance Context UI audit, the governed weather-semantics reconciliation work,
or any feature delivery. It only surfaces in the from-base replay path, which no
current runtime depends on.

### Suggested remediation
- Rewrite the offending early **data** migration(s) so they reference only the
  schema valid at their own revision: replace the live ORM `User` query with an
  explicit Core `text()` / `sa.table(...)`/`sa.column(...)` construct that lists
  *only* the columns guaranteed to exist at that point in the chain. Never import
  and query mapped ORM models inside a migration.
- After the fix, add a CI check that performs a clean `alembic upgrade head` (and
  ideally `downgrade base`) against a throwaway empty database to keep the chain
  replayable going forward.

### Cross-references
- Already noted in agent memory under `backend-test-harness` (test-harness
  gotchas + the from-base replay defect).
