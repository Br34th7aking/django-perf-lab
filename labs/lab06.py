from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Post


class PostDetailBad(APIView):
    def get(self, request, pk):
        post = Post.objects.get(pk=pk)
        return Response({
            "title": post.title,
            "comment_count": post.comment_stats()["count"],
            "latest_comment": post.comment_stats()["latest"],
            "has_discussion": post.comment_stats()["count"] > 0,
            "preview": f"{post.title} ({post.comment_stats()['count']} comments)"
        })


class PostDetailGood(APIView):
    def get(self, request, pk):
        post = Post.objects.get(pk=pk)
        return Response({
            "title": post.title,
            "comment_count": post.comment_stats_cached["count"],
            "latest_comment": post.comment_stats_cached["latest"],
            "has_discussion": post.comment_stats_cached["count"] > 0,
            "preview": f"{post.title} ({post.comment_stats_cached['count']} comments)"
        })