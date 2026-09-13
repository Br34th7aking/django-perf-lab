import pytest

from core.models import Author, Category, Comment, Post
from labs import lab16


class FakeRedis:
    def __init__(self):
        self.hashes = {}

    def hincrby(self, name, key, amount=1):
        bucket = self.hashes.setdefault(name, {})
        bucket[key] = bucket.get(key, 0) + amount
        return bucket[key]

    def recompute_count(self, name):
        return sum(self.hashes.get(name, {}).values())


class RecordingCache:
    """Dict-backed cache stand-in that records the timeout of every set()."""

    def __init__(self):
        self.store = {}
        self.timeouts = []

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, timeout=None):
        self.timeouts.append(timeout)
        self.store[key] = value


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(lab16, "r", fake)
    return fake


@pytest.fixture
def recording_cache(monkeypatch):
    recorder = RecordingCache()
    monkeypatch.setattr(lab16, "cache", recorder)
    return recorder


@pytest.fixture
def category(db):
    author = Author.objects.create(name="A")
    cat = Category.objects.create(name="C")
    post = Post.objects.create(title="p", body="x", author=author, category=cat)
    Comment.objects.create(post=post, body="one")
    Comment.objects.create(post=post, body="two")
    return cat


def test_bad_and_good_agree(client, category, fake_redis, recording_cache):
    bad = client.get(f"/labs/16/bad/{category.pk}/").json()
    good = client.get(f"/labs/16/good/{category.pk}/").json()
    assert bad == good == {"category": category.pk, "comments": 2}


def test_warm_hits_skip_recompute(client, category, fake_redis, recording_cache):
    for _ in range(3):
        client.get(f"/labs/16/bad/{category.pk}/")
    assert fake_redis.recompute_count("lab16:recomputes:bad") == 1


def test_bad_ttl_is_fixed(client, category, fake_redis, recording_cache):
    client.get(f"/labs/16/bad/{category.pk}/")
    assert recording_cache.timeouts == [lab16.TTL]


def test_good_ttl_jitters_within_bounds(client, category, fake_redis, recording_cache):
    for _ in range(10):
        recording_cache.store.clear()
        client.get(f"/labs/16/good/{category.pk}/")
    assert len(recording_cache.timeouts) == 10
    assert all(0.8 * lab16.TTL <= t <= 1.2 * lab16.TTL for t in recording_cache.timeouts)
    assert len(set(recording_cache.timeouts)) > 1
