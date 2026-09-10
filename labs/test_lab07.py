import pytest
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import Author, Category, Like, Post, PostLike


@pytest.fixture
def liked_posts(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    posts = [
        Post.objects.create(title=f"p{i}", body="x", author=author, category=category)
        for i in range(3)
    ]
    ct = ContentType.objects.get_for_model(Post)
    for post in posts:
        for _ in range(2):
            Like.objects.create(content_type=ct, object_id=post.id)
            PostLike.objects.create(post=post)
    return posts


def test_generic_and_concrete_counts_agree(client, liked_posts):
    bad = client.get("/labs/07/bad/").json()
    good = client.get("/labs/07/good/").json()
    assert bad == good
    assert all(row["like_count"] == 2 for row in good)


def test_feed_explodes_per_like(client, liked_posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/07/feed/").status_code == 200
    assert len(ctx) == 1 + 6  # list + one lazy resolution per like


def test_feed_fixed_batches_by_type(client, liked_posts):
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/labs/07/feed-fixed/").status_code == 200
    assert len(ctx) == 2  # list + one batched fetch per content type
