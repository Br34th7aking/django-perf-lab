import pytest

from core.models import Author, Category, Comment, Post, PostLike


@pytest.fixture
def post_with_relations(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    post = Post.objects.create(title="p", body="x", author=author, category=category)
    for i in range(2):
        Comment.objects.create(post=post, body=f"c{i}")
    for _ in range(3):
        PostLike.objects.create(post=post)
    return post


def test_wrong_endpoint_multiplies_counts(client, post_with_relations):
    row = client.get("/labs/09/wrong/").json()[0]
    assert row["comment_count"] == 6  # 2 comments x 3 likes: the cross-product
    assert row["like_count"] == 6


def test_bad_endpoint_is_correct(client, post_with_relations):
    row = client.get("/labs/09/bad/").json()[0]
    assert (row["comment_count"], row["like_count"]) == (2, 3)


def test_raw_sql_matches_orm_results(client, post_with_relations):
    assert client.get("/labs/09/good/").json() == client.get("/labs/09/bad/").json()
