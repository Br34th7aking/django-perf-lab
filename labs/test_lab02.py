import pytest
from django.db import connection

from core.models import Author, Category, Post


@pytest.fixture
def dated_posts(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    for day in ["2026-06-03", "2026-06-05", "2026-08-01"]:
        Post.objects.create(
            title=f"p-{day}", body="x", author=author, category=category,
            published_on=day, published_on_idx=day,
        )


def test_index_exists_on_indexed_column(db):
    with connection.cursor() as cur:
        indexes = connection.introspection.get_constraints(cur, "core_post")
    assert any(
        c["columns"] == ["published_on_idx"] and c["index"]
        for c in indexes.values()
    ), "published_on_idx has no index — was the migration applied?"


def test_endpoints_filter_the_week(client, dated_posts):
    for url in ["/labs/02/bad/", "/labs/02/good/"]:
        response = client.get(url)
        assert response.status_code == 200
        assert len(response.json()) == 2  # only the two June posts