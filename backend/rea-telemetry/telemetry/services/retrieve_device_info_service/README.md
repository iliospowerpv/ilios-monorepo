# Retrieve Device Info Service

A service that retrieves available info about an existing device of an existing site using an authorized token from a supported data provider.

The service is deployed as a [Cloud Function](https://console.cloud.google.com/functions/details/us-central1/retrieve_device_info_service?project=prj-ilios-telemetry), which is called on-demand by the platform backend.

See the corresponding [Cloud Build Configuration](./cloudbuild.yaml) and [Cloud Build Trigger](https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=prj-ilios-telemetry) for more details.

## Overview

### Request (POST)

```json
{
    "data_provider": "<DATA_PROVIDER>",
    "token_secret_id": "<TOKEN_SECRET_ID>",
    "site_id": "<SITE_ID>",
    "device_id": "<DEVICE_ID>"
}
```

**NOTE**. The token is provided indirectly as a reference to a secret from [Secret Manager](https://console.cloud.google.com/security/secret-manager?project=prj-ilios-telemetry).

### Response (200 OK)

```json
{
    "id": "<DEVICE_ID>",
    "name": "<DEVICE_NAME>",
    "category": "<DEVICE_CATEGORY>",
    "serial_number": "<DEVICE_SERIAL_NUMBER>",
    "gateway_id": "<DEVICE_GATEWAY_ID>",
    "function_id": "<DEVICE_FUNCTION_ID>",
    "driver": "<DEVICE_DRIVER>",
    "last_update_ts": "<DEVICE_LAST_UPDATE_TS>"
}
```

**NOTE**. All fields are optional (nullable) except for `id` and `name`.

## Local Development

### Installation

```shell
pip install -r requirements.txt
```

### Execution

```shell
CLOUD=0 functions-framework --target=retrieve_device_info_service --debug
```
