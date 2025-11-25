import os

from google.cloud import run_v2
from locust import HttpUser, between, task


class CloudRunJobUser(HttpUser):
    wait_time = between(60, 120)

    @task
    def invoke_cloud_run_job(self) -> None:
        project_id = os.getenv("PROJECT_NUMBER", "602280418311")
        location = os.getenv("LOCATION", "us-west1")
        job_name = (
            f"projects/{project_id}/locations/{location}/jobs/key-value-extraction-job"
        )
        data = {
            "id": 7,
            "file_url": "gs://doc_ai_storage/site-lease/documents/"
            "Brixmor-Blue Sky Felicita Plaza Lease - 7_17_19 "
            "(BSU Sig_ Deed Included).pdf",
            "agreement_type": "Site Lease",
            "detect_poison_pills": 1,
        }
        file_id = data["id"]
        file_url = data["file_url"]
        agreement_type = data["agreement_type"]
        poison_pills_detection = data["detect_poison_pills"]

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

        for _ in range(1):
            _ = client.run_job(request=request)
