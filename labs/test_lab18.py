from collections import defaultdict

import pytest

from core.models import Author, Category, Comment, Post
from labs import lab18, tasks


class StubRedis:
    def __init__(self):
        self.counts = defaultdict(int)

    def incr(self, key):
        self.counts[key] += 1
        return self.counts[key]


@pytest.fixture
def stub_redis(monkeypatch):
    stub = StubRedis()
    monkeypatch.setattr(tasks, "r", stub)
    return stub


@pytest.fixture
def delay_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(lab18.mark_comment_processed, "delay", calls.append)
    return calls


@pytest.fixture
def post(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    return Post.objects.create(id=1, title="p", body="x", author=author, category=category)


def test_bad_publishes_inside_the_transaction(
    client, post, delay_calls, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks() as callbacks:
        client.post("/labs/18/bad/")
    assert len(delay_calls) == 1  # already on the wire before commit
    assert callbacks == []


def test_good_publishes_only_after_commit(
    client, post, delay_calls, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        client.post("/labs/18/good/")
    assert delay_calls == []  # nothing published while the transaction is open
    assert len(callbacks) == 1
    callbacks[0]()  # the commit happens
    assert len(delay_calls) == 1


def test_task_processes_an_existing_comment(post, stub_redis):
    comment = Comment.objects.create(post=post, body="hello")
    tasks.mark_comment_processed(comment.pk)
    comment.refresh_from_db()
    assert comment.body == "hello [processed]"
    assert stub_redis.counts == {"lab18:processed": 1}


def test_task_counts_a_ghost_for_a_missing_comment(db, stub_redis):
    with pytest.raises(Comment.DoesNotExist):
        tasks.mark_comment_processed(999_999)
    assert stub_redis.counts == {"lab18:ghost": 1}
