# Process Telemetry Data Job

The job is deployed as a [Cloud Function](https://console.cloud.google.com/functions/details/us-central1/process_telemetry_data_job?project=prj-ilios-telemetry), which is automatically triggered by a [Cloud Scheduler](https://console.cloud.google.com/cloudscheduler/jobs/edit/us-central1/process_telemetry_data_job_trigger?project=prj-ilios-telemetry) but can also be triggered on-demand if necessary.

See the corresponding [Cloud Build Configuration](./cloudbuild.yaml) and [Cloud Build Trigger](https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=prj-ilios-telemetry) for more details.

## Overview

Once triggered, either on-demand or by schedule, the job updates tables and views for each platform dataset (one per platform environment) in BigQuery (check the `platform_{enviroment}` datasets for more insight),
maintaining the up-to-date mapping between external devices from data providers and internal devices from platform environments, as defined by telemetry configs in Firestore (check the `{environment}-telemetry-config` collections for more insight).

## Local Development

### Installation

```shell
pip install -r requirements.txt
```

### Execution

```shell
CLOUD=0 functions-framework --target=process_telemetry_data_job --debug
```
