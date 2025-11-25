from locust import SequentialTaskSet, task

from locust_tests.common import LoginTasks


class ProfileTaskSet(SequentialTaskSet, LoginTasks):

    def on_start(self):
        self.login()

    @task
    def retrieve_self_profile(self):
        self.client.get("/api/users/account/me", headers=self.parent.auth_header)

    @task
    def stop(self):
        self.interrupt()
