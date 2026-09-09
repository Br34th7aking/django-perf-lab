import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Author, Category, Post


@pytest.fixture
def three_posts(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    for i in range(3):
        Post.objects.create(title=f"p{i}", body="x" * 100, author=author, category=category)


def test_full_fetch_drags_body(client, three_posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/04/full/").status_code == 200
    assert '"body"' in ctx[0]["sql"]


def test_only_skips_body(client, three_posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/04/only/").status_code == 200
    assert '"body"' not in ctx[0]["sql"]
    assert len(ctx) == 1


def test_values_skips_body_single_query(client, three_posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/04/values/").status_code == 200
    assert '"body"' not in ctx[0]["sql"]
    assert len(ctx) == 1


def test_defer_trap_pays_per_row(client, three_posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/04/defer-trap/").status_code == 200
    assert len(ctx) == 1 + 3  # list query + one refetch per touched body
