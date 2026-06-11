# REA Telemetry

> ## ⚠️ DECOMMISSIONING — DO NOT EXTEND
>
> **Status:** Legacy. Superseded by **Native Telemetry Ingestion V2** inside
> `backend/ilios-server` (in-process readings ingestion + rollups in PostgreSQL,
> with the `TelemetrySchedulerRunner` daemon for scheduled pulls). This external
> GCP pipeline (`prj-ilios-telemetry`: Cloud Scheduler → Pub/Sub → Cloud Functions
> → BigQuery, with the target list in Firestore) is **no longer the source of
> truth for app-facing telemetry** and is on a removal path.
>
> **As of the "Telemetry V2 Legacy Removal — phase 1" sprint:** every app-facing
> consumer of this pipeline (Firestore mapping sync, BigQuery health/chart/device/
> company fallbacks) is gated in `backend/ilios-server` behind the off-by-default
> `legacy_telemetry_enabled` flag. With the flag off (the default), the platform
> reads telemetry exclusively from the V2 PostgreSQL store and returns honest
> `N/A` where this pipeline used to supply data — it never fabricates `0`.
>
> **Rules while this code still exists:**
> - Do **not** add new callers or re-point V2 code at this pipeline.
> - Do **not** re-enable it merely to backfill expected/loss values for V2 sites —
>   that logic now lives natively in `backend/ilios-server` (expected-baseline
>   service + metric catalog).
> - Treat anything here as reference-only for porting formulas; new work belongs in
>   the in-process V2 stack.
> - Hard deletion of this directory is a **separate, later** sprint. This sprint is
>   isolation-only (additive/reversible).
>
> **Still in use (NOT part of this isolation):** the discovery *services*
> (`verify_token_service`, `retrieve_sites_service`, `retrieve_devices_service`,
> `retrieve_device_info_service`) are still called by the V2 onboarding wizard for
> credential validation and site/device discovery via `TelemetryFuncHTTPClient`.
> Only the ingestion **jobs** (`request`/`fetch`/`ingest`/`process`) are off the
> app-facing data path. Do **not** remove the services as part of phase 1.
>
> See `backend/ilios-server/app/settings.py` (`legacy_telemetry_enabled`) and
> `backend/ilios-server/app/helpers/telemetry/legacy_flag.py` for the gate.

A set of components (jobs & services) of the telemetry data pipeline.

The components of the pipeline are deployed in the `prj-ilios-telemetry` project on [Google Cloud](https://console.cloud.google.com/welcome?project=prj-ilios-telemetry).

## Overview

### Jobs

Each job is an integral part of the pipeline, representing a distinct stage within it.

- [Request Telemetry Data Job](./telemetry/jobs/0_request_telemetry_data_job/README.md)
- [Fetch Telemetry Data Job](./telemetry/jobs/1_fetch_telemetry_data_job/README.md)
- [Ingest Telemetry Data Job](./telemetry/jobs/2_ingest_telemetry_data_job/README.md)
- [Process Telemetry Data Job](./telemetry/jobs/3_process_telemetry_data_job/README.md)

### Services

Each service acts as a mediator between the internal platform backend and external data providers, allowing the platform's users to gradually modify the pipeline's configuration over time.

- [Verify Token Service](./telemetry/services/verify_token_service/README.md)
- [Retrieve Sites Service](./telemetry/services/retrieve_sites_service/README.md)
- [Retrieve Devices Service](./telemetry/services/retrieve_devices_service/README.md)
- [Retrieve Device Info Service](./telemetry/services/retrieve_device_info_service/README.md)

## Local Development

### Installation

```shell
pip install -r requirements-dev.txt
```

### Formatting (black + isort)

```shell
make lint
```

### Linting (black + isort + flake8)

```shell
make lint
```
