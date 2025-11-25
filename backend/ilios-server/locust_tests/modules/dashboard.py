from locust import SequentialTaskSet, task

from locust_tests.common import LoginTasks


class DashboardPageTaskSet(SequentialTaskSet, LoginTasks):

    def on_start(self):
        self.login()

    @task
    class DashboardActions(SequentialTaskSet):
        @task
        def retrieve_dashboard_tasks(self):
            self.client.get("/api/account/dashboard/tasks", headers=self.parent.parent.auth_header)

        @task
        def retrieve_dashboard_notifications(self):
            self.client.get("/api/account/dashboard/notifications", headers=self.parent.parent.auth_header)

        @task
        def stop(self):
            self.interrupt()

    @task
    def stop(self):
        self.interrupt()
