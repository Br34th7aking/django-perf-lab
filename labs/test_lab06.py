import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Author, Category, Comment, Post


@pytest.fixture
def post_with_comments(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    post = Post.objects.create(title="p", body="x", author=author, category=category)
    for i in range(3):
        Comment.objects.create(post=post, body=f"c{i}")
    return post


def test_bad_pays_per_call(client, post_with_comments):
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(f"/labs/06/bad/{post_with_comments.pk}/")
    assert response.status_code == 200
    assert len(ctx) == 9  # 1 post + 4 calls x 2 queries


def test_good_pays_once(client, post_with_comments):
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(f"/labs/06/good/{post_with_comments.pk}/")
    assert response.status_code == 200
    assert len(ctx) == 3  # 1 post + 2 queries on first access, then cache

    bad = client.get(f"/labs/06/bad/{post_with_comments.pk}/").json()
    assert bad == response.json()  # identical payload, fewer queries
