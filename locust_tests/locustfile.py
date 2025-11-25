from locust import HttpUser, SequentialTaskSet, between, task

from locust_tests.modules import AssetManagementModuleTaskSet, DashboardPageTaskSet, OnMModuleTaskSet, ProfileTaskSet


class ModulesGroupedTasks(SequentialTaskSet):
    """Register of tasks sets by modules"""

    tasks = [ProfileTaskSet, DashboardPageTaskSet, AssetManagementModuleTaskSet, OnMModuleTaskSet]


class APITestUser(HttpUser):
    tasks = [ModulesGroupedTasks]
    # Simulate user wait time between requests
    wait_time = between(1, 5)

    @task
    def health_check(self):
        self.client.get("/health")
