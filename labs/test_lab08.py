import pytest
from django.contrib.contenttypes.models import ContentType

from core.models import Author, Category, Like, Post


@pytest.fixture
def liked_post(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    post = Post.objects.create(title="p", body="x", author=author, category=category)
    ct = ContentType.objects.get_for_model(Post)
    Like.objects.create(content_type=ct, object_id=post.id)
    return post


def test_cached_and_uncached_agree(client, liked_post):
    # cachalot is deliberately absent from test settings; both endpoints compute.
    assert client.get("/labs/08/good/").json() == client.get("/labs/08/bad/").json()


def test_orm_write_nets_zero(client, liked_post):
    before = Like.objects.count()
    assert client.get("/labs/08/orm-write/").status_code == 200
    assert Like.objects.count() == before  # create + delete


def test_raw_write_inserts_one_like(client, liked_post):
    before = Like.objects.count()
    assert client.get("/labs/08/raw-write/").status_code == 200
    assert Like.objects.count() == before + 1
