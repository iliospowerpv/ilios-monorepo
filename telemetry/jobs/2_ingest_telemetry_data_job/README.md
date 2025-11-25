# Ingest Telemetry Data Job

The job is deployed as a [Dataflow Job](https://console.cloud.google.com/dataflow/jobs?project=prj-ilios-telemetry), which reads from Pub/Sub and writes to BigQuery in real-time.

See the corresponding [Cloud Build Configuration](./cloudbuild.yaml) and [Cloud Build Trigger](https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=prj-ilios-telemetry) for more details.

## Overview

The job runs 24/7, operating entirely in real-time. It pulls messages from a [Pub/Sub Subscription](https://console.cloud.google.com/cloudpubsub/subscription/detail/ingest-telemetry-data-subscription?project=prj-ilios-telemetry)
associated with a [Pub/Sub Topic](https://console.cloud.google.com/cloudpubsub/topic/detail/ingest-telemetry-data-topic?project=prj-ilios-telemetry), which the previous job publishes to (explore the [Fetch Telemetry Data Job](./../1_fetch_telemetry_data_job/README.md) to learn more).
These messages are converted to records and inserted into the corresponding tables of a [BigQuery Dataset](https://console.cloud.google.com/bigquery?project=prj-ilios-telemetry&ws=!1m4!1m3!3m2!1sprj-ilios-telemetry!2stelemetry_raw) based on the `category` attribute (`points` vs `alerts`).

## Local Development

### Installation

```shell
pip install -r requirements.txt
```

### Execution

```shell
python main.py --subscription_id=projects/prj-ilios-telemetry/subscriptions/ingest-telemetry-data-subscription-sandbox --dataset_id=prj-ilios-telemetry:telemetry_raw_sandbox
```

**NOTE.** Make sure not to pull any messages from the subscription [ingest-telemetry-data-subscription](https://console.cloud.google.com/cloudpubsub/subscription/detail/ingest-telemetry-data-subscription?project=prj-ilios-telemetry)
and not to insert any records to the tables of the dataset [telemetry_raw](https://console.cloud.google.com/bigquery?project=prj-ilios-telemetry&ws=!1m4!1m3!3m2!1sprj-ilios-telemetry!2stelemetry_raw) during development to avoid intercepting the production pipeline.
Use the subscription [ingest-telemetry-data-subscription-sandbox](https://console.cloud.google.com/cloudpubsub/subscription/detail/ingest-telemetry-data-subscription-sandbox?project=prj-ilios-telemetry)
and the dataset [telemetry_sandbox](https://console.cloud.google.com/bigquery?project=prj-ilios-telemetry&ws=!1m4!1m3!3m2!1sprj-ilios-telemetry!2stelemetry_sandbox) for this purpose instead.
