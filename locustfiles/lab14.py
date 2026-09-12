from locust import HttpUser, between, tag, task


class DashboardUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @tag("bad")
    @task
    def bad(self):
        self.client.get("/labs/14/bad/")

    
    @tag("good")
    @task
    def good(self):
        self.client.get("/labs/14/good/")