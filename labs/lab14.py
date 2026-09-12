from django.db.models import Count
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Category, Post


def _build_dashboard():
    top_posts = (
        Post.objects.annotate(cc=Count("comments"))
        .order_by("-cc")
        .values("id", "title", "cc")[:10]
    )
    category_counts = (
        Category.objects.annotate(n_posts=Count("posts")).order_by("-n_posts").values("name", "n_posts")
    )

    return {
        "top_posts": list(top_posts),
        "categories": list(category_counts),
    }


@api_view(["GET"])
def dashboard_bad(request):
    return Response(_build_dashboard())

