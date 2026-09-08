import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Author, Category, Post, Tag


@pytest.fixture
def posts(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    tag = Tag.objects.create(name="tag-1")

    for i in range(5):
        post = Post.objects.create(title=f"p{i}", body="x", author=author, category=category)
        post.tags.add(tag)


def test_bad_endpoint_has_n_plus_one(client, posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/01/bad/").status_code == 200
    
    assert len(ctx) == 16 # 1 + 3 per post


def test_good_endpoint_is_constant(client, posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/01/good/").status_code == 200
    
    assert len(ctx) == 2

def test_trap_refilters_per_post(client, posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/01/trap/").status_code == 200
    assert len(ctx) == 7  # 1 posts + 1 discarded prefetch + 1 filter per post


def test_trap_fixed_is_constant(client, posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/01/trap-fixed/").status_code == 200
    assert len(ctx) == 2