gcloud functions deploy key_value_extraction_trigger \
               --gen2 \
               --runtime=python310 \
               --region=us-west1 \
               --source=. \
               --entry-point=cloud_run_trigger \
               --memory=256MiB --timeout=30 --trigger-http --allow-unauthenticated
