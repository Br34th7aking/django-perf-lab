import pytest

from core.models import Author, Category, Post


@pytest.fixture
def many_posts(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    Post.objects.bulk_create(
        Post(title=f"p{i}", body="x", author=author, category=category) for i in range(25)
    )


def test_bad_returns_everything(client, many_posts):
    data = client.get("/labs/05/bad/").json()
    assert len(data) == 25  # response grows with the table — that's the bug


def test_good_returns_one_page(client, many_posts):
    data = client.get("/labs/05/good/").json()
    assert data["count"] == 25
    assert len(data["results"]) == 20  # constant regardless of table size
