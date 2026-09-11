from django.db import connection
from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Post


class PostStatsWrong(APIView):
    """Two to-many joins multiply: counts come back as comments x likes."""

    def get(self, request):
        qs = (
            Post.objects.annotate(cc=Count("comments"), lc=Count("likes"))
            .order_by("id")
            .values("id", "title", "cc", "lc")[:20]
        )
        return Response(
            [
                {"id": r["id"], "title": r["title"],
                 "comment_count": r["cc"], "like_count": r["lc"]}
                for r in qs
            ]
        )


class PostStatsBad(APIView):

    def get(self, request):
        qs = (
            Post.objects.annotate(
                cc=Count("comments", distinct=True),
                lc=Count("likes", distinct=True),
            )
            .order_by("id")
            .values("id", "title", "cc", "lc")[:20]
        )
        return Response(
            [
                {"id": r["id"], "title": r["title"],
                 "comment_count": r["cc"], "like_count": r["lc"]}
                for r in qs
            ]
        )

    
class PostStatsGood(APIView):
    """Correlated subqueries: each relation counted independently, no cross join."""

    def get(self, request):
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.title,
                    (SELECT count(*) FROM core_comment c
                       WHERE c.post_id = p.id) AS comment_count,
                    (SELECT count(*) FROM core_postlike l
                    WHERE l.post_id = p.id) AS like_count
                FROM core_post p
                ORDER BY p.id
                LIMIT 20
                """
            )
            rows = cur.fetchall()
        return Response(
            [
                {"id": r[0], "title": r[1], "comment_count": r[2], "like_count": r[3]}
                for r in rows
            ]
        )