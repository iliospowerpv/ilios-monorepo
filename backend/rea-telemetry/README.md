# REA Telemetry

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
