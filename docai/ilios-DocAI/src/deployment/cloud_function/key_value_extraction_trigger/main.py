import logging.config
import os

import functions_framework
from flask import Request
from google.cloud import run_v2


logger = logging.getLogger(__name__)
logging.config.fileConfig("logging.conf", disable_existing_loggers=False)


@functions_framework.http
def cloud_run_trigger(request: Request) -> str:
    """Trigger execution of GCP cloud job for Key-value extraction.
    IliOS backend app would use the payload of this function as a result of User
    frontend trigger action.
    """
    project_id = os.getenv("PROJECT_NUMBER", "602280418311")
    location = os.getenv("LOCATION", "us-west1")
    job_name = (
        f"projects/{project_id}/locations/{location}/jobs/key-value-extraction-job"
    )
    data = request.get_json()
    file_id = data["id"]
    file_url = data["file_url"]
    agreement_type = data["agreement_type"]
    poison_pills_detection = data["detect_poison_pills"]
    logger.info(f"Trigger connection received for file: {file_id}")
    logger.info(f"File URL: {file_url}")
    logger.info(f"Agreement type: {agreement_type}")
    logger.info(f"Detect poison pills: {poison_pills_detection}")

    client = run_v2.JobsClient()
    override_spec = {
        "container_overrides": [
            {
                "env": [
                    {"name": "FILE_ID", "value": str(file_id)},
                    {"name": "FILE_URL", "value": str(file_url)},
                    {"name": "AGREEMENT_TYPE", "value": str(agreement_type)},
                    {
                        "name": "DETECT_POISON_PILLS",
                        "value": str(poison_pills_detection),
                    },
                ]
            }
        ]
    }
    # Initialize request argument(s)
    request = run_v2.RunJobRequest(name=job_name, overrides=override_spec)

    # Make the request
    _ = client.run_job(request=request)

    return f"Job scheduled for file: {file_id}"
