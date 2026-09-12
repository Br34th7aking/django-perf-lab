import pytest
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Author, Category, Comment, Post


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def posts(db):
    author = Author.objects.create(name="A")
    c1 = Category.objects.create(name="C1")
    c2 = Category.objects.create(name="C2")
    p1 = Post.objects.create(title="p1", body="x", author=author, category=c1)
    Post.objects.create(title="p2", body="x", author=author, category=c2)
    Comment.objects.create(post=p1, body="hi")
    return p1


def test_bad_and_good_agree(client, posts):
    assert client.get("/labs/14/bad/").json() == client.get("/labs/14/good/").json()


def test_warm_hit_runs_zero_queries(client, posts):
    client.get("/labs/14/good/")
    with CaptureQueriesContext(connection) as ctx:
        client.get("/labs/14/good/")
    assert len(ctx.captured_queries) == 0


def test_good_serves_stale_copy_after_write(client, posts):
    before = client.get("/labs/14/good/").json()
    posts.title = "changed"
    posts.save()
    assert client.get("/labs/14/bad/").json() != before
    assert client.get("/labs/14/good/").json() == before
