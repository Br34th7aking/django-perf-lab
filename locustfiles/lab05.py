from locust import HttpUser, between, tag, task


class Reader(HttpUser):
    wait_time = between(0.5, 2)

    @tag("bad")
    @task
    def all_posts(self):
        self.client.get("/labs/05/bad/")

    @tag("good")
    @task
    def paged_posts(self):
        self.client.get("/labs/05/good/?page=3")