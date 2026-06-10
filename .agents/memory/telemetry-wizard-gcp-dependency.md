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
- **Device Mapping (step 2) is now fully V2 DB-backed.** The cache read
  (`GET /v2/provider-accounts/{id}/external-sites/{ext_site}/devices`), the explicit
  `sync-devices` (single live provider call, never wipes cache on failure), and the bulk
  device-mapping save (`POST /v2/sites/{id}/device-mappings`) all go through the V2 path. The
  wizard maps *iliOS* devices (from `/sites/{id}/eligible-devices`, i.e. `site.devices` with
  category inverter/module/weather_station) onto synced DAS devices; the DAS devices only render
  as a dropdown *inside* each eligible-device row. **Gotcha:** a project with zero
  telemetry-eligible devices shows a blank mapping step even when DAS devices synced fine — there
  is no DAS→iliOS device import, so devices must be created in the project first. Step 2 has an
  explicit empty-state for this case.

**Why it matters / how to apply:**
- If telemetry mapping "spins and shows nothing," suspect the v1 live-fetch hitting missing GCP
  ADC; the DB-backed V2 path is the fix for *reads*.
- Always surface React Query `isError`/`error` in multi-step wizards — the original silent
  failure was a query whose error was never read (default retry:3 → ~7s spinner → blank).
- The wizard's site-mapping *save* and the whole device-mapping flow were made GCP-free by building
  V2 DB-only endpoints (chosen over best-effort Firestore or configuring GCP creds).
- "Empty device list" on the mapping step is usually NOT a sync failure — check
  `telemetry_external_devices` (DAS cache) AND the project's `devices` rows separately; a populated
  cache + zero eligible project devices is the common cause.
- A uvicorn `--reload` master keeps the env it booted with; only a fresh boot/deploy re-reads env
  vars. A `Settings` field whose type mismatches its env value (here `gcp_project_id: int` vs the
  string `"ilios-prod-telemetry"`) won't crash the already-running reloader but fails *every*
  fresh boot — a "running" backend can be a ghost that dies on the next restart. GCP project ids
  are strings; `gcp_project_id` is `Optional[str]`.
- v2's `_require_account` auth is stricter than v1's hub-aware `get_hub_connections`: a
  portfolio-shared connection owned by a hub company the user can't directly access will 404 on
  external-sites. Fine for company-owned accounts; revisit if portfolio-shared must work.
