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
- **Site Mapping (save): now V2 DB-only.** `PUT /api/telemetry/v2/sites/{site_id}/mapping`
  upserts the single mapping row (keyed on the unique `site_id`) directly in Postgres with **no
  provider/Firestore call**: the external site must already be in the V2 `telemetry_external_sites`
  cache (else 404 "sync first"), the display name is read from that cache, and provenance
  (`company_id`, `provider_account_id`/`connection_id`, `created_by_user_id`, timestamps) is
  stamped. The legacy v1 save (SQL-then-Firestore, rollback-on-Firestore-failure) still exists but
  the wizard no longer calls it.
- **Device Mapping (step 2) is still v1/GCP** (list + bulk save) — intentionally unchanged.

**Why it matters / how to apply:**
- If telemetry mapping "spins and shows nothing," suspect the v1 live-fetch hitting missing GCP
  ADC; the DB-backed V2 path is the fix for *reads*.
- Always surface React Query `isError`/`error` in multi-step wizards — the original silent
  failure was a query whose error was never read (default retry:3 → ~7s spinner → blank).
- The wizard's site-mapping *save* was made GCP-free by building a V2 DB-only upsert endpoint
  (chosen over best-effort Firestore or configuring GCP creds). Device Mapping save is the next
  candidate if it must also work without GCP.
- A uvicorn `--reload` master keeps the env it booted with; only a fresh boot/deploy re-reads env
  vars. A `Settings` field whose type mismatches its env value (here `gcp_project_id: int` vs the
  string `"ilios-prod-telemetry"`) won't crash the already-running reloader but fails *every*
  fresh boot — a "running" backend can be a ghost that dies on the next restart. GCP project ids
  are strings; `gcp_project_id` is `Optional[str]`.
- v2's `_require_account` auth is stricter than v1's hub-aware `get_hub_connections`: a
  portfolio-shared connection owned by a hub company the user can't directly access will 404 on
  external-sites. Fine for company-owned accounts; revisit if portfolio-shared must work.
