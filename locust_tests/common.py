from locust import TaskSet, task

from locust_tests.config import locust_secrets


class LoginTasks(TaskSet):
    """Logs user in and saves `auth_header` to the parent entity.
    Please, note - parent relationship should reflect proper nesting level:
     if `auth_header` attribute is used in the TaskSet which is nested to the other TaskSet which inherits LoginTasks,
     you should call it by `self.parent.parent.auth_header`"""

    @task
    def login(self):
        response = self.client.post(
            "/api/auth/login", json={"email": locust_secrets["USER_EMAIL"], "password": locust_secrets["USER_PASSWORD"]}
        )
        token = response.json()["access_token"]
        self.parent.auth_header = {"Authorization": f"Bearer {token}"}
