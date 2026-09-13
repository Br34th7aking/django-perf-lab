from types import SimpleNamespace

import pytest

from labs import lab17, tasks


@pytest.fixture
def sleep_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(tasks.time, "sleep", calls.append)
    return calls


@pytest.fixture
def delay_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(
        lab17.send_confirmation_email,
        "delay",
        lambda *a: calls.append(a) or SimpleNamespace(id="fake-task-id"),
    )
    return calls


def test_bad_does_the_work_in_the_request(client, sleep_calls, delay_calls):
    response = client.post("/labs/17/bad/")
    assert response.json() == {"status": "subscribed"}
    assert sleep_calls  # the slow part ran inline
    assert not delay_calls


def test_good_defers_and_returns_a_receipt(client, sleep_calls, delay_calls):
    response = client.post("/labs/17/good/")
    assert response.json() == {"status": "accepted", "task_id": "fake-task-id"}
    assert delay_calls == [(1,)]
    assert not sleep_calls  # nothing slow happened in the request
