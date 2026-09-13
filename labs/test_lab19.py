from collections import defaultdict

import pytest

from labs import lab19, tasks


class StubRedis:
    def __init__(self):
        self.lists = defaultdict(list)

    def rpush(self, key, value):
        self.lists[key].append(value)
        return len(self.lists[key])


@pytest.fixture
def stub_redis(monkeypatch):
    stub = StubRedis()
    monkeypatch.setattr(tasks, "r", stub)
    return stub


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(tasks.time, "sleep", lambda s: None)


@pytest.fixture
def enqueued(monkeypatch):
    calls = []

    def fake_apply_async(*, args, queue):
        calls.append((args, queue))

    monkeypatch.setattr(lab19.bulk_task, "apply_async", fake_apply_async)
    monkeypatch.setattr(lab19.urgent_task, "apply_async", fake_apply_async)
    return calls


def test_flood_defaults_to_the_shared_queue(client, enqueued):
    response = client.post("/labs/19/flood/")
    assert response.json() == {"queued": 200, "queue": "celery"}
    assert len(enqueued) == 200
    assert all(queue == "celery" for _, queue in enqueued)


def test_flood_routes_to_the_bulk_queue(client, enqueued):
    response = client.post("/labs/19/flood/?queue=bulk")
    assert response.json() == {"queued": 200, "queue": "bulk"}
    assert all(queue == "bulk" for _, queue in enqueued)


def test_urgent_stays_on_the_default_queue(client, enqueued):
    client.post("/labs/19/urgent/")
    assert len(enqueued) == 1
    assert enqueued[0][1] == "celery"


def test_tasks_record_their_wait_time(stub_redis, no_sleep):
    tasks.bulk_task(0.0)
    tasks.urgent_task(0.0)
    assert list(stub_redis.lists) == ["lab19:wait:bulk", "lab19:wait:urgent"]
    for waits in stub_redis.lists.values():
        assert len(waits) == 1 and waits[0] > 0
