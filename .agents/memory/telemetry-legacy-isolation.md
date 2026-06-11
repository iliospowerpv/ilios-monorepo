---
name: Telemetry legacy isolation flag
description: How the legacy GCP telemetry pipeline is gated off behind legacy_telemetry_enabled, and which legacy pieces V2 still depends on (hybrid).
---

# Legacy telemetry isolation (`legacy_telemetry_enabled`)

The legacy GCP telemetry pipeline (`backend/rea-telemetry`: Cloud Scheduler → Pub/Sub
→ Cloud Functions → BigQuery, target list in Firestore) is being decommissioned in
favor of in-process Native Telemetry Ingestion V2 (PostgreSQL) in
`backend/ilios-server`. Phase 1 ISOLATES the legacy side effects behind an
off-by-default flag; ZERO hard deletes.

**Flag:** `legacy_telemetry_enabled: bool = False` in `app/settings.py`. Settings use
`case_sensitive=True`, so the env var key MUST be lowercase `legacy_telemetry_enabled`.
Callsites read it via the predicate in `app/helpers/telemetry/legacy_flag.py`.

**What the flag gates (legacy-ONLY side effects):**
- Firestore mapping sync in create/update/delete device mapping.
- BigQuery fallbacks: `/health` last-report, device_helper, company energy-attribute
  extension, and legacy chart helpers.

**Invariant — never fabricate zero.** With the flag OFF (default), legacy paths return
honest `N/A` / empty / `None`, NEVER `0`. A fabricated `0` reads as "site produced
nothing", which is a data-integrity lie. The frontend mirrors this: a resolver maps
`expected_state` (fallback to the `expected_baseline_available` boolean) to
show-expected vs. "N/A + reason", and never plots a fabricated baseline.

**LANDMINE (why the gate wraps the WHOLE block):** legacy
`create_device_mapping_for_telemetry` DELETED the just-written DB row inside its
Firestore `except`. So you must gate the entire Firestore try/except, not just the FS
call — otherwise an FS error (or flag-off short-circuit done wrong) loses the DB write.
With the flag off, DB writes for mappings must still persist.

**HYBRID — do NOT assume "legacy = unused".** The V2 onboarding wizard still depends on
parts of the legacy stack:
- The legacy router stays MOUNTED (wizard calls legacy connections, SiteForm legacy
  site-mapping, legacy readiness/health).
- `TelemetryFuncHTTPClient` + the rea-telemetry discovery *services*
  (`verify_token`, `retrieve_sites`, `retrieve_devices`, `retrieve_device_info`) are
  still used for V2 credential validation and site/device discovery.
- Only the 4 ingestion *jobs* (`request`/`fetch`/`ingest`/`process`) are off the
  app-facing data path. KEEP: generic BQ client, credential_store, GCP Secret Manager,
  bq_data_sync characteristics WRITE, V2 tables/endpoints, scheduler, DD parsing.

**Why:** decommissioning a pipeline that a live onboarding flow still leans on must be
reversible and surgical — flip data sourcing to V2, but don't pull discovery/credential
plumbing the wizard needs. Hard deletion is a later, separate sprint.
