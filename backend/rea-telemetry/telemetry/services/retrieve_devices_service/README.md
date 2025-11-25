# Retrieve Devices Service

A service that retrieves a list of available devices for an existing site using an authorized token from a supported data provider.

The service is deployed as a [Cloud Function](https://console.cloud.google.com/functions/details/us-central1/retrieve_devices_service?project=prj-ilios-telemetry), which is called on-demand by the platform backend.

See the corresponding [Cloud Build Configuration](./cloudbuild.yaml) and [Cloud Build Trigger](https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=prj-ilios-telemetry) for more details.

## Overview

### Request (POST)

```json
{
    "data_provider": "<DATA_PROVIDER>",
    "token_secret_id": "<TOKEN_SECRET_ID>",
    "site_id": "<SITE_ID>"
}
```

**NOTE**. The token is provided indirectly as a reference to a secret from [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=prj-ilios-telemetry).

### Response (200 OK)

```json
[
    {
        "id": "<DEVICE_ID>",
        "name": "<DEVICE_NAME>"
    }
]
```

## Local Development

### Installation

```shell
pip install -r requirements.txt
```

### Execution

```shell
CLOUD=0 functions-framework --target=retrieve_devices_service --debug
```
