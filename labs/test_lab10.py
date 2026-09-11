import pytest

from core.models import Author, Category, Comment, Post


@pytest.fixture
def posts(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    return [
        Post.objects.create(title=f"p{i}", body="x", author=author, category=category)
        for i in range(2)
    ]


def test_signals_maintain_counter(posts):
    post = posts[0]
    c1 = Comment.objects.create(post=post, body="a")
    Comment.objects.create(post=post, body="b")
    post.refresh_from_db()
    assert post.comment_count == 2

    c1.delete()
    post.refresh_from_db()
    assert post.comment_count == 1


def test_bulk_create_bypasses_counter(posts):
    post = posts[0]
    Comment.objects.bulk_create([Comment(post=post, body=f"c{i}") for i in range(3)])
    post.refresh_from_db()
    assert post.comment_count == 0  # documented drift: bulk_create skips signals


def test_endpoints_agree(client, posts):
    for i, post in enumerate(posts):
        for j in range(i + 1):
            Comment.objects.create(post=post, body=f"c{j}")
    assert client.get("/labs/10/bad/").json() == client.get("/labs/10/good/").json()
