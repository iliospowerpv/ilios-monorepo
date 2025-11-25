#!/usr/bin/env bash

function="${1}"

[ -z "${function}" ] && echo 'ERROR: Function is not provided.' && exit 1

if [[ "${function}" == *_job ]]; then
  category='jobs'
elif [[ "${function}" == *_service ]]; then
  category='services'
else
  echo "ERROR: Function must be either job or service." && exit 1
fi

[ ! -d "./telemetry/${category}/${function}/" ] && echo 'ERROR: Function does not exist.' && exit 1

rm -rf "./.deploy/${category}/${function}/" && mkdir -p "./.deploy/${category}/${function}/"
cp -r "./telemetry/${category}/${function}/" "./.deploy/${category}/${function}/" && cd "./.deploy/${category}/${function}/"

if [[ "${function}" == *_job ]]; then
  function="${function#*_}"
fi

if [ -f '.env' ]; then
  # Enable automatic export of variables before loading.
  # Disable automatic export of variables after loading.
  set -a && source '.env' && set +a
fi

gcloud functions deploy "${function}" \
  --project="${PROJECT:=prj-ilios-telemetry}" \
  --region="${REGION:=us-central1}" \
  --gen2 \
  --trigger-http \
  --allow-unauthenticated \
  --runtime="${RUNTIME:=python312}" \
  --memory="${MEMORY:=256Mi}" \
  --cpu="${CPU:=250m}" \
  --timeout="${TIMEOUT:=15}" \
  --min-instances="${MIN_INSTANCES:=0}" \
  --max-instances="${MAX_INSTANCES:=16}" \
  --concurrency="${CONCURRENCY:=1}" \
  --entry-point="${function}" \
  --update-build-env-vars="GIT_BRANCH=$(git branch --show-current),GIT_COMMIT=$(git rev-parse HEAD)"
