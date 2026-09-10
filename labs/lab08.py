from cachalot.api import cachalot_disabled
from django.db import connection
from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Like, Post


def like_counts():
    qs = Post.objects.annotate(n=Count("generic_likes")).order_by("id")[:20]
    return [{"id": p.id, "likes": p.n} for p in qs]


class LikeCountsUncached(APIView):

    def get(self, request):
        with cachalot_disabled():
            return Response(like_counts())


class LikeCountsCached(APIView):

    def get(self, request):
        return Response(like_counts())


class OrmWrite(APIView):
    def get(self, request):
        post = Post.objects.order_by("id").first()
        Like.objects.create(content_object=post).delete()
        return Response({"invalidated": "core_like"})


class RawWrite(APIView):
    def get(self, request):
        first_id = Post.objects.order_by("id").values_list("id", flat=True).first()
        with connection.cursor() as cur:
            cur.execute(
                "INSERT INTO core_like (uuid, created_at, last_modified,"
                " content_type_id, object_id) "
                "SELECT gen_random_uuid(), now(), now(), ct.id, %s"
                " FROM django_content_type ct"
                " WHERE ct.model = 'post' AND ct.app_label = 'core'",
                [first_id],
            )
        return Response({"raw_like_added_to_post": first_id})