import pytest
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
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
    author = Author.objects.create(name="Ada")
    category = Category.objects.create(name="C")
    out = [
        Post.objects.create(title=f"p{i}", body="x", author=author, category=category)
        for i in range(3)
    ]
    Comment.objects.create(post=out[0], body="hi")
    return out


def test_pages_render_same_content(client, posts):
    bad = client.get("/labs/15/bad/").content
    good = client.get("/labs/15/good/").content
    assert b"Ada" in bad
    for fragment in [b"p0", b"p1", b"p2", b"1 comments"]:
        assert fragment in bad and fragment in good


def test_warm_render_runs_zero_queries(client, posts):
    client.get("/labs/15/good/")
    with CaptureQueriesContext(connection) as ctx:
        client.get("/labs/15/good/")
    assert len(ctx.captured_queries) == 0


def test_edited_post_rerenders_only_its_fragment(client, posts):
    client.get("/labs/15/good/")
    posts[1].title = "edited"
    posts[1].save()
    cache.delete(make_template_fragment_key("lab15_page"))
    with CaptureQueriesContext(connection) as ctx:
        response = client.get("/labs/15/good/")
    assert b"edited" in response.content
    assert len(ctx.captured_queries) == 3  # post list + 2 counts for the edited post


def test_flush_forces_full_rerender(client, posts):
    client.get("/labs/15/good/")
    with CaptureQueriesContext(connection) as ctx:
        client.get("/labs/15/good/?flush=1")
    assert len(ctx.captured_queries) > 3
