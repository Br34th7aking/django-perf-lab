from django.contrib.postgres.search import SearchQuery, SearchVector
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Post


def payload(qs):
    return {"count": qs.count(), "sample": list(qs.values_list("id", flat=True)[:10])}


class SearchIContains(APIView):

    def get(self, request):
        q = request.GET.get("q", "tempor")
        return Response(payload(Post.objects.filter(body__icontains=q)))


class SearchFTSNaive(APIView):
    def get(self, request):
        q = request.GET.get("q", "tempor")
        qs = Post.objects.annotate(
            v=SearchVector("title", "body", config="english")
        ).filter(v=SearchQuery(q, config="english"))
        return Response(payload(qs))


class SearchFTSIndexed(APIView):

    def get(self, request):
        q = request.GET.get("q", "tempor")
        qs = Post.objects.filter(search_vector=SearchQuery(q, config="english"))
        return Response(payload(qs))

