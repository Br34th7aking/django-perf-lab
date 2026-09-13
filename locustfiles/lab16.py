import random

from locust import HttpUser, between, tag, task


class CategoryDashboardUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @tag("bad")
    @task
    def bad(self):
        self.client.get(f"/labs/16/bad/{random.randint(1, 20)}/", name="/labs/16/bad/[id]/")

    @tag("good")
    @task
    def good(self):
        self.client.get(f"/labs/16/good/{random.randint(1, 20)}/", name="/labs/16/good/[id]/")
