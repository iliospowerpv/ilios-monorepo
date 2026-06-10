---
name: Telemetry data ingestion & demo mode
description: Where telemetry time-series actually comes from, why a site shows "no data", and the V2->Firestore config gap. Read when telemetry health/readiness/performance shows nothing.
---

## The real data pull is NOT in this FastAPI app
Time-series ingestion is an external GCP pipeline in the separate `backend/rea-telemetry` service (deployed to the `prj-ilios-telemetry` GCP project), not an in-process job:
- GCP Cloud Scheduler (`request_telemetry_data_job_trigger`, 15-min cadence) → job `0_request_telemetry_data_job` reads telemetry configs from **Firestore** (`stream_documents`) → publishes to Pub/Sub → `1_fetch...` calls DAS provider (Also Energy etc.) with creds from GCP Secret Manager → `2_ingest...` writes BigQuery → `3_process...` aggregates.
- The iliOS app only **reads** BigQuery (`TelemetryDeviceBigQuery.get_device_last_reported`, etc.) and only **configures** mappings/credentials. There is **no in-app "pull now" endpoint** and no APScheduler/Celery. You cannot trigger a pull from the app; it requires running the GCP job via Console/gcloud against that project.
- `TelemetryFuncHTTPClient` (telemetry_cloud_function_client.py) only does synchronous config tasks (validate_token, list external sites/devices). It does NOT pull production data.

## Demo mode bypasses BigQuery entirely
- `is_demo_mode()` is True iff env `DEMO_TELEMETRY` in (true/1/yes). When on, `BaseTelemetryBigQuery` logs "Telemetry running in DEMO mode — BigQuery bypassed" and `execute_bq_function` returns `get_demo_bq_data(...)` (synthetic, generated on-demand: last_report 2-10 min ago, bell-curve solar power, etc.).
- **Demo data is only generated for demo sites/devices** — sites whose `companies.is_demo = true`. `get_demo_bq_data` scopes by `is_demo_site`/`is_demo_device`; non-demo ids return `[]`.
- Consequence: in a DEMO_TELEMETRY env, a **real (non-demo) company's site shows "no data" no matter how long you wait** — demo path skips it AND real BigQuery is bypassed. Verify telemetry UX against actual demo sites instead.

## V2 wizard mappings do NOT sync to Firestore (config gap)
- Only the **V1** helpers (`telemetry_helper.py` create/update/delete_*_for_telemetry) write Firestore via `FirestoreClient`. The **V2** site- and device-mapping endpoints (`routers/telemetry/v2.py`) are explicitly Postgres-only ("does not touch any GCP / Firestore pipeline").
- Since the external puller reads its target list from Firestore, a site mapped only through the V2 wizard would **not be picked up by the scheduled pull even in a fully GCP-wired environment**. Closing this needs a Postgres→Firestore sync on the V2 save path (or migrating the puller to read Postgres).

**Why:** "devices are mapped but telemetry still shows nothing" is ambiguous; the cause is almost always one of these three layers, not the mapping itself.
**How to apply:** when telemetry shows no data, check in order: (1) is `DEMO_TELEMETRY` on? (2) is the site's company `is_demo`? (3) did the mapping reach Firestore (V1 path) or only Postgres (V2)?
