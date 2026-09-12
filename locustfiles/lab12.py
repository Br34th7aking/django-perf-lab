from locust import HttpUser, between, tag, task


class ViewTracker(HttpUser):
    wait_time = between(0.1, 0.3)

    @tag("bad")
    @task
    def bad(self):
        self.client.get("/labs/12/bad/1/")

    @tag("good")
    @task
    def good(self):
        self.client.get("/labs/12/good/1/")
