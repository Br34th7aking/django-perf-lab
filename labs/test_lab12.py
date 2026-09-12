import fnmatch

import pytest
import redis as redislib
from django.core.management import call_command

from core.models import Author, Category, Post


class FakeRedis:
    """In-memory stand-in: CI has no redis, and tests must not touch dev counters."""

    def __init__(self):
        self.store = {}

    @staticmethod
    def _s(key):
        return key.decode() if isinstance(key, bytes) else key

    def incr(self, key):
        key = self._s(key)
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    def get(self, key):
        value = self.store.get(self._s(key))
        return None if value is None else str(value).encode()

    def getdel(self, key):
        value = self.store.pop(self._s(key), None)
        return None if value is None else str(value).encode()

    def scan_iter(self, pattern):
        return [k.encode() for k in list(self.store) if fnmatch.fnmatch(k, pattern)]


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr("labs.lab12.r", fake)
    monkeypatch.setattr(redislib.Redis, "from_url", classmethod(lambda cls, url: fake))
    return fake


@pytest.fixture
def post(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    return Post.objects.create(title="p", body="x", author=author, category=category)


def test_bad_tracker_updates_column(client, post, fake_redis):
    client.get(f"/labs/12/bad/{post.pk}/")
    post.refresh_from_db()
    assert post.view_count == 1
    assert fake_redis.store == {}


def test_good_tracker_stays_in_redis(client, post, fake_redis):
    client.get(f"/labs/12/good/{post.pk}/")
    client.get(f"/labs/12/good/{post.pk}/")
    post.refresh_from_db()
    assert post.view_count == 0
    data = client.get(f"/labs/12/count/{post.pk}/").json()
    assert data == {"post": post.pk, "views": 2, "flushed": 0, "pending": 2}


def test_flush_moves_pending_without_changing_truth(client, post, fake_redis):
    client.get(f"/labs/12/bad/{post.pk}/")
    client.get(f"/labs/12/good/{post.pk}/")
    client.get(f"/labs/12/good/{post.pk}/")

    call_command("flush_views")

    data = client.get(f"/labs/12/count/{post.pk}/").json()
    assert data == {"post": post.pk, "views": 3, "flushed": 3, "pending": 0}
