import pytest

from core.models import Author, Category, Post


@pytest.fixture
def searchable_posts(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    Post.objects.create(
        title="cooking", body="a recipe about baking bread", author=author, category=category
    )
    Post.objects.create(
        title="cycling", body="notes on bike maintenance", author=author, category=category
    )


def test_icontains_finds_substring(client, searchable_posts):
    assert client.get("/labs/13/bad/?q=bread").json()["count"] == 1


def test_indexed_fts_matches_stemmed_words(client, searchable_posts):
    # 'baked' and 'baking' share the stem 'bake': FTS matches, substring does not
    assert client.get("/labs/13/good/?q=baked").json()["count"] == 1
    assert client.get("/labs/13/bad/?q=baked").json()["count"] == 0


def test_naive_and_indexed_fts_agree(client, searchable_posts):
    for q in ["bread", "bike", "xylophone"]:
        assert (
            client.get(f"/labs/13/naive/?q={q}").json()
            == client.get(f"/labs/13/good/?q={q}").json()
        )
