# Request Telemetry Data Job

The job is deployed as a [Cloud Function](https://console.cloud.google.com/functions/details/us-central1/request_telemetry_data_job?project=prj-ilios-telemetry), which is automatically triggered by a [Cloud Scheduler](https://console.cloud.google.com/cloudscheduler/jobs/edit/us-central1/request_telemetry_data_job_trigger?project=prj-ilios-telemetry) but can also be triggered on-demand if necessary.

See the corresponding [Cloud Build Configuration](./cloudbuild.yaml) and [Cloud Build Trigger](https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=prj-ilios-telemetry) for more details.

## Overview

Once triggered, either on-demand or by schedule, the job reads and parses all documents from each collection of telemetry configs (one per platform environment) in [Firestore](https://console.cloud.google.com/firestore/databases/-default-/data/panel?project=prj-ilios-telemetry).
It extracts all mapped (platform environment → data provider) devices along with their context from each config.
Finally, it publishes each payload (device + context) as a message to a [Pub/Sub Topic](https://console.cloud.google.com/cloudpubsub/topic/detail/fetch-telemetry-data-topic?project=prj-ilios-telemetry), which the next job is subscribed to (explore the [Fetch Telemetry Data Job](./../1_fetch_telemetry_data_job/README.md) to learn more).

### Message Payload

```
{
    "data_provider": "<DATA_PROVIDER>",  /* STRING (ENUM) */ 
    "token_secret_id": "<TOKEN_SECRET_ID>",  /* STRING */ 
    "site_id": "<SITE_ID>",  /* STRING (EXTERNAL) */
    "device_id": "<DEVICE_ID>",  /* STRING (EXTERNAL) */
    "platform": {
        "environment": "<ENVIRONMENT>",  /* STRING (ENUM) */
        "company_id": <COMPANY_ID>,  /* INTEGER */
        "site_id": <SITE_ID>,  /* INTEGER (INTERNAL) */
        "device_id": <DEVICE_ID>,  /* INTEGER (INTERNAL) */
    },
}
```

## Local Development

### Installation

```shell
pip install -r requirements.txt
```

### Execution

```shell
CLOUD=0 FETCH_TELEMETRY_DATA_TOPIC_NAME=fetch-telemetry-data-topic-sandbox functions-framework --target=request_telemetry_data_job --debug
```

**NOTE.** Make sure not to publish any messages to the topic [fetch-telemetry-data-topic](https://console.cloud.google.com/cloudpubsub/topic/detail/fetch-telemetry-data-topic?project=prj-ilios-telemetry) during development to avoid intercepting the production pipeline.
Use the topic [fetch-telemetry-data-topic-sandbox](https://console.cloud.google.com/cloudpubsub/topic/detail/fetch-telemetry-data-topic-sandbox?project=prj-ilios-telemetry) for this purpose instead.
