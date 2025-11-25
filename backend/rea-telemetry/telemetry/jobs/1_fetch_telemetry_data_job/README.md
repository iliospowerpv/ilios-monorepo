# Fetch Telemetry Data Job

The job is deployed as a [Cloud Function](https://console.cloud.google.com/functions/details/us-central1/fetch_telemetry_data_job?project=prj-ilios-telemetry), which is automatically triggered by a [Pub/Sub Subscription](https://console.cloud.google.com/cloudpubsub/subscription/detail/fetch-telemetry-data-subscription?project=prj-ilios-telemetry) but can also be triggered on-demand if necessary.

See the corresponding [Cloud Build Configuration](./cloudbuild.yaml) and [Cloud Build Trigger](https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=prj-ilios-telemetry) for more details.

## Overview

Once triggered, either on-demand or by a [Pub/Sub Subscription](https://console.cloud.google.com/cloudpubsub/subscription/detail/fetch-telemetry-data-subscription?project=prj-ilios-telemetry) associated with a [Pub/Sub Topic](https://console.cloud.google.com/cloudpubsub/topic/detail/fetch-telemetry-data-topic?project=prj-ilios-telemetry), which the previous job publishes to (explore the [Request Telemetry Data Job](./../0_request_telemetry_data_job/README.md) to learn more),
the job looks up a device in its cache in Firestore (check the `temetry-cache` collection for more insight) to get the last fetch timestamp.
It fetches all points/alerts measured/occurred during the latest interval (from the last fetch timestamp up to the current timestamp) for the device from the corresponding data provider.
It updates the cache to set the last fetch timestamp for the device to the current timestamp.
Finally, it publishes each payload (device + point/alert) as a message to a [Pub/Sub Topic](https://console.cloud.google.com/cloudpubsub/topic/detail/ingest-telemetry-data-topic?project=prj-ilios-telemetry), which the next job is subscribed to (explore the [Ingest Telemetry Data Job](./../2_ingest_telemetry_data_job/README.md) to learn more).

### Message Payload

#### Point (`message.category = "points"`)

```
{
    "data_provider": "<DATA_PROVIDER>",  /* STRING (ENUM) */ 
    "site_id": "<SITE_ID>",  /* STRING */ 
    "device_id": "<DEVICE_ID>",  /* STRING */ 
    "point_tag": "<POINT_TAG>",  /* STRING (ENUM) */
    "point_data_value": <POINT_DATA_VALUE>,  /* NUMBER (INTEGER | FLOAT) */
    "point_data_ts": "<POINT_DATA_TS>",  /* STRING (DATETIME) */
}
```

#### Alert (`message.category = "alerts"`)

```
{
    "data_provider": "<DATA_PROVIDER>",  /* STRING (ENUM) */ 
    "site_id": "<SITE_ID>",  /* STRING */ 
    "device_id": "<DEVICE_ID>",  /* STRING */ 
    "alert_id": "<ALERT_ID>",  /* STRING */
    "alert_type": "<ALERT_TYPE>",  /* STRING */
    "alert_severity": "<ALERT_SEVERITY>",  /* STRING (ENUM) */
    "alert_message": "<ALERT_MESSAGE>",  /* STRING */
    "alert_is_resolved": <ALERT_IS_RESOLVED>,  /* BOOLEAN */
    "alert_start_ts": "<ALERT_START_TS>",  /* STRING (DATETIME) */
}
```

## Local Development

### Installation

```shell
pip install -r requirements.txt
```

### Execution

```shell
CLOUD=0 INGEST_TELEMETRY_DATA_TOPIC_NAME=ingest-telemetry-data-topic-sandbox functions-framework --target=fetch_telemetry_data_job --debug
```

**NOTE.** Make sure not to publish any messages to the topic [ingest-telemetry-data-topic](https://console.cloud.google.com/cloudpubsub/topic/detail/ingest-telemetry-data-topic?project=prj-ilios-telemetry) during development to avoid intercepting the production pipeline.
Use the topic [ingest-telemetry-data-topic-sandbox](https://console.cloud.google.com/cloudpubsub/topic/detail/ingest-telemetry-data-topic-sandbox?project=prj-ilios-telemetry) for this purpose instead.
