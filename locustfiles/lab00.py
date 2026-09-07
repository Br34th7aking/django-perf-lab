from locust import HttpUser, between, task

class BasicUser(HttpUser):
    wait_time = between(0.5, 2)

    @task
    def health(self):
        self.client.get("/labs/health")