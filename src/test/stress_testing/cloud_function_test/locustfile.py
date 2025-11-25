from locust import HttpUser, between, task


class CloudFunctionUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def invoke_cloud_function(self) -> None:
        data = {
            "id": 123,
            "file_url": "gs://doc_ai_storage/site-lease/documents/"
            "Brixmor-Blue Sky Felicita Plaza Lease - 7_17_19 "
            "(BSU Sig_ Deed Included).pdf",
            "agreement_type": "Site Lease",
            "detect_poison_pills": 1,
        }
        address = (
            "https://us-west1-prj-ilios-ai.cloudfunctions.net/"
            "key_value_extraction_trigger"
        )
        for _ in range(10):
            self.client.get(address, json=data)
