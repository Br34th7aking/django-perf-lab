from locust import HttpUser, between, tag, task


class SubscribeUser(HttpUser):
    wait_time = between(0.5, 1.5)

    @tag("bad")
    @task
    def bad(self):
        self.client.post("/labs/17/bad/")

    
    @tag("good")
    @task
    def good(self):
        self.client.post("/labs/17/good/")