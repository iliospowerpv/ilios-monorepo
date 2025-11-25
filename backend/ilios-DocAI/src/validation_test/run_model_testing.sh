#!/bin/bash
IMAGE_NAME="model_testing"

docker build --platform linux/amd64 -t "${IMAGE_NAME}" -f src/validation_test/Dockerfile .
docker run \
		-e GOOGLE_API_KEY=${GOOGLE_API_KEY} \
		-e PROJECT_ID=${PROJECT_ID} \
        -e DOC_AI_LOCATION=${DOC_AI_LOCATION} \
        -e DOC_AI_PROCESSOR_ID=${DOC_AI_PROCESSOR_ID} \
        -e GOOGLE_APPLICATION_CREDENTIALS=/app/notebooks/prj-ilios-ai.json \
        -e PYTHONPATH=/app \
        -e PWD=/app \
        -e LOCATION=${LOCATION} \
        -e GCS_VECTOR_STORE_BUCKET=${GCS_VECTOR_STORE_BUCKET} \
        -e VECTOR_STORE_INDEX_ENDPOINT_ID=${VECTOR_STORE_INDEX_ENDPOINT_ID} \
        -e VECTOR_STORE_INDEX_ID=${VECTOR_STORE_INDEX_ID} \
        -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
        -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
        -e MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI} \
        -e MLFLOW_TRACKING_USERNAME=${MLFLOW_TRACKING_USERNAME} \
        -e MLFLOW_TRACKING_PASSWORD=${MLFLOW_TRACKING_PASSWORD} \
		-d --name ${IMAGE_NAME}-container \
		-p 8080:8080 ${IMAGE_NAME}