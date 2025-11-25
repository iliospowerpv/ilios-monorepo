from locust import SequentialTaskSet, task

from locust_tests.common import LoginTasks


class OnMModuleTaskSet(SequentialTaskSet, LoginTasks):

    def on_start(self):
        self.login()

    @task
    class OnMActions(SequentialTaskSet):
        company_id = None
        site_id = None

        @task
        def retrieve_onm_companies_list(self):
            response = self.client.get(
                "/api/operations-and-maintenance/companies/", headers=self.parent.parent.auth_header
            )
            if response.json()["items"]:
                self.company_id = response.json()["items"][0]["id"]

        @task
        def retrieve_onm_company_dashboard(self):
            if self.company_id:
                self.client.get(
                    f"/api/operations-and-maintenance/companies/{self.company_id}",
                    headers=self.parent.parent.auth_header,
                )
                self.client.get(
                    f"/api/operations-and-maintenance/companies/{self.company_id}/actual-production-chart",
                    headers=self.parent.parent.auth_header,
                )
                self.client.get(
                    f"/api/operations-and-maintenance/companies/{self.company_id}/actual-vs-expected-production-chart",
                    headers=self.parent.parent.auth_header,
                )
                self.client.get(
                    f"/api/operations-and-maintenance/companies/{self.company_id}/loses-for-a-day-chart",
                    headers=self.parent.parent.auth_header,
                )

        @task
        def retrieve_onm_company_sites(self):
            if self.company_id:
                response = self.client.get(
                    f"/api/operations-and-maintenance/companies/{self.company_id}/sites",
                    headers=self.parent.parent.auth_header,
                )
                if response.json()["items"]:
                    self.site_id = response.json()["items"][0]["id"]

        @task
        def retrieve_onm_site_dashboard(self):
            if self.site_id:
                self.client.get(
                    f"/api/operations-and-maintenance/sites/{self.site_id}", headers=self.parent.parent.auth_header
                )
                self.client.get(
                    f"/api/operations-and-maintenance/sites/{self.site_id}/actual-production-chart",
                    headers=self.parent.parent.auth_header,
                )
                self.client.get(
                    f"/api/operations-and-maintenance/sites/{self.site_id}/past-performance-chart",
                    headers=self.parent.parent.auth_header,
                )
                self.client.get(
                    f"/api/operations-and-maintenance/sites/{self.site_id}/devices-overview-section",
                    headers=self.parent.parent.auth_header,
                )
                self.client.get(
                    f"/api/operations-and-maintenance/sites/{self.site_id}/actual-vs-expected-chart",
                    headers=self.parent.parent.auth_header,
                )
                self.client.get(
                    f"/api/operations-and-maintenance/sites/{self.site_id}/inverters-performance-chart",
                    headers=self.parent.parent.auth_header,
                )

        @task
        def retrieve_onm_site_devices(self):
            if self.site_id:
                self.client.get(
                    f"/api/operations-and-maintenance/sites/{self.site_id}/devices",
                    headers=self.parent.parent.auth_header,
                )

        @task
        def stop(self):
            self.interrupt()

    @task
    def stop(self):
        self.interrupt()
