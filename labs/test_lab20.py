import pytest
from celery import current_app
from django.conf import settings

from labs import tasks


class StubRedis:
    def __init__(self):
        self.lists = {}

    def rpush(self, key, value):
        self.lists.setdefault(key, []).append(value)
        return len(self.lists[key])


@pytest.fixture
def stub_redis(monkeypatch):
    stub = StubRedis()
    monkeypatch.setattr(tasks, "r", stub)
    return stub


def test_schedule_points_at_a_registered_task():
    entry = settings.CELERY_BEAT_SCHEDULE["flush-pending-views"]
    assert entry["task"] in current_app.tasks
    assert entry["schedule"] > 0


def test_task_flushes_and_records_the_run(monkeypatch, stub_redis):
    commands = []
    monkeypatch.setattr(tasks, "call_command", commands.append, raising=False)
    monkeypatch.setattr("django.core.management.call_command", commands.append)
    tasks.flush_pending_views()
    assert commands == ["flush_views"]
    runs = stub_redis.lists["lab20:runs"]
    assert len(runs) == 1 and runs[0] > 0
