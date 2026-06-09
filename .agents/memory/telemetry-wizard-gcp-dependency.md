---
name: Telemetry wizard GCP dependency
description: Which telemetry flows need live GCP (Secret Manager / Firestore) vs. the DB-backed V2 path, and how that shapes the project-level Telemetry Setup Wizard.
---

# Telemetry: two systems, and the wizard straddles both

There are two coexisting telemetry stacks that share the **same `das_connections` table**
(a v1 "connection" row and a v2 "provider account" row are the *same* row / same id):

- **Legacy v1** — live provider calls gated on **GCP Secret Manager** for credentials and
  **Firestore** for ingestion config (and **BigQuery** for readiness). Fails hard in any
  environment without GCP Application Default Credentials (dev, and prod until ADC is set):
  `google.auth.default()` raises `DefaultCredentialsError`.
- **V2** — provider accounts + external-sites, **DB-backed** with a credential-store that has a
  non-GCP fallback. Test + sync-sites + list external-sites all work without live GCP. This is
  why a user can sync 71 sites at the company level while the v1 live-fetch 502s.

## The project-level Telemetry Setup Wizard
- **Site Mapping (list):** now reads the already-synced sites from the **V2 external-sites**
  endpoint (DB-backed). Because connection_id == provider_account_id, the wizard's selected
  connection id is passed straight through as the v2 account id.
- **Save path (still v1/GCP):** creating/updating a site mapping writes SQL **then** calls
  Firestore, and on *any* Firestore failure it **rolls back the SQL row and re-raises**. So the
  save fails without GCP even though the list now works. Device Mapping (list + bulk save) is
  likewise v1/GCP-dependent.

**Why it matters / how to apply:**
- If telemetry mapping "spins and shows nothing," suspect the v1 live-fetch hitting missing GCP
  ADC; the DB-backed V2 path is the fix for *reads*.
- Always surface React Query `isError`/`error` in multi-step wizards — the original silent
  failure was a query whose error was never read (default retry:3 → ~7s spinner → blank).
- Making the wizard's *save* work without GCP is a product decision (make Firestore sync
  best-effort vs. build a V2 DB-only mapping endpoint vs. configure GCP creds) — it changes
  production write semantics, so confirm direction before changing it.
- v2's `_require_account` auth is stricter than v1's hub-aware `get_hub_connections`: a
  portfolio-shared connection owned by a hub company the user can't directly access will 404 on
  external-sites. Fine for company-owned accounts; revisit if portfolio-shared must work.
