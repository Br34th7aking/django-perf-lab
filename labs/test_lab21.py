import pytest
from django.core.cache import cache
from waffle.models import Flag
from waffle.testutils import override_flag

from core.models import Author, Category, Post


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def posts(db):
    author = Author.objects.create(name="A")
    category = Category.objects.create(name="C")
    Post.objects.create(
        title="baking", body="a recipe about baking bread", author=author, category=category
    )


def test_flag_off_uses_icontains(client, posts):
    with override_flag("fts-search", active=False):
        data = client.get("/labs/21/search/?q=bread").json()
    assert data["engine"] == "icontains"
    assert data["count"] == 1


def test_flag_on_uses_fts(client, posts):
    with override_flag("fts-search", active=True):
        data = client.get("/labs/21/search/?q=bread").json()
    assert data["engine"] == "fts"
    assert data["count"] == 1


def test_engines_disagree_on_stems(client, posts):
    # 'baked' stems to 'bake': FTS matches, substring does not — result
    # semantics shift with the engine, which is why it rolls out gradually
    with override_flag("fts-search", active=True):
        assert client.get("/labs/21/search/?q=baked").json()["count"] == 1
    with override_flag("fts-search", active=False):
        assert client.get("/labs/21/search/?q=baked").json()["count"] == 0


def test_percent_flag_sets_rollout_cookie(client, posts):
    # pins the DRF wiring: waffle must see the underlying HttpRequest,
    # or the middleware never learns a roll happened and sets no cookie
    Flag.objects.create(name="fts-search", percent=50)
    response = client.get("/labs/21/search/?q=bread")
    assert "dwf_fts-search" in response.cookies


def test_flags_endpoint_reports_state(client, db):
    Flag.objects.create(name="fts-search", everyone=True)
    assert client.get("/labs/21/flags/").json() == {"fts-search": True}
