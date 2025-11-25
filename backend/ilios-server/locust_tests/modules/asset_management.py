from locust import SequentialTaskSet, task

from locust_tests.common import LoginTasks


class AssetManagementModuleTaskSet(SequentialTaskSet, LoginTasks):

    def on_start(self):
        self.login()

    @task
    class AMActions(SequentialTaskSet):
        @task
        def retrieve_am_companies(self):
            self.client.get("/api/companies/", headers=self.parent.parent.auth_header)

        @task
        def retrieve_am_sites(self):
            self.client.get("/api/sites/", headers=self.parent.parent.auth_header)

        @task
        def stop(self):
            self.interrupt()

    @task
    def stop(self):
        self.interrupt()
