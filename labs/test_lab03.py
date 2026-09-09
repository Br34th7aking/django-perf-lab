import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Author, Category, Comment, Post


@pytest.fixture
def one_comment(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    post = Post.objects.create(title="p", body="x", author=author, category=category)
    Comment.objects.create(post=post, body="hi")


def test_bad_existence_check_counts(client, one_comment):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/03/bad/").json()["has_comments"] is True
    assert "COUNT" in ctx[0]["sql"].upper()


def test_good_existence_check_stops_at_one_row(client, one_comment):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/03/good/").json()["has_comments"] is True
    assert "LIMIT 1" in ctx[0]["sql"].upper()
    assert "COUNT" not in ctx[0]["sql"].upper()


def test_counted_pagination_pays_a_count_query(client, one_comment):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/03/page-counted/").status_code == 200
    assert len(ctx) == 2


def test_nocount_pagination_skips_it(client, one_comment):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/03/page-nocount/").status_code == 200
    assert len(ctx) == 1


def test_count_endpoints_respond(client, one_comment):
    assert client.get("/labs/03/count-exact/").json()["count"] == 1
    assert isinstance(client.get("/labs/03/count-approx/").json()["count"], int)
