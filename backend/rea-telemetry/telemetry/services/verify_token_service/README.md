# Verify Token Service

A service that verifies whether a token is authorized to access a supported data provider.

The service is deployed as a [Cloud Function](https://console.cloud.google.com/functions/details/us-central1/verify_token_service?project=prj-ilios-telemetry), which is called on-demand by the platform backend.

See the corresponding [Cloud Build Configuration](./cloudbuild.yaml) and [Cloud Build Trigger](https://console.cloud.google.com/cloud-build/triggers;region=us-central1?project=prj-ilios-telemetry) for more details.

## Overview

### Request (POST)

```json
{
    "data_provider": "<DATA_PROVIDER>",
    "token": "<TOKEN>"
}
```

### Response (200 OK)

```json
{
    "message": "OK"
}
```

### Response (401 Unauthorized)

```json
{
    "message": "Unauthorized"
}
```

## Local Development

### Installation

```shell
pip install -r requirements.txt
```

### Execution

```shell
CLOUD=0 functions-framework --target=verify_token_service --debug
```
