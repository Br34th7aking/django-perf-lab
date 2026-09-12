import os

import redis
from django.db.models import F
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Post

r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


def pending_key(pk):
    return f"post:{pk}:pending_views"


class TrackViewBad(APIView):
    """One postgres UPDATE per page view: row lock + WAL + dead tuple, per hit."""

    def get(self, request, pk):
        Post.objects.filter(pk=pk).update(view_count=F("view_count") + 1)
        return Response({"tracked": pk})


class TrackViewGood(APIView):
    """One in-memory increment per page view. postgres sees nothing until flush."""

    def get(self, request, pk):
        r.incr(pending_key(pk))
        return Response({"tracked": pk})


class ViewCountRead(APIView):
    """Truth = flushed base in postgres + pending delta in redis."""

    def get(self, request, pk):
        base = Post.objects.using("default").values_list(
            "view_count", flat=True
        ).get(pk=pk)
        pending = int(r.get(pending_key(pk)) or 0)

        return Response({
            "post": pk,
            "views": base + pending,
            "flushed": base, 
            "pending": pending
        })