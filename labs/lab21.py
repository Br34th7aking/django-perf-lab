from django.contrib.postgres.search import SearchQuery
from rest_framework.decorators import api_view
from rest_framework.response import Response
from waffle import flag_is_active
from waffle.models import Flag

from core.models import Post

FLAG = "fts-search"


def _payload(qs):
    return {"count": qs.count(), "sample": list(qs.values_list("id", flat=True)[:10])}


@api_view(["GET"])
def search(request):
    q = request.GET.get("q", "tempor")
    # DRF wraps HttpRequest; waffle must see the underlying one or the
    # rollout cookie is never set (middleware reads request.waffles there)
    if flag_is_active(request._request, FLAG):
        data = _payload(Post.objects.filter(search_vector=SearchQuery(q, config="english")))
        data["engine"] = "fts"
    else:
        data = _payload(Post.objects.filter(body__icontains=q))
        data["engine"] = "icontains"
    return Response(data)


@api_view(["GET"])
def flags(request):
    return Response(
        {f.name: flag_is_active(request._request, f.name) for f in Flag.objects.all()}
    )
