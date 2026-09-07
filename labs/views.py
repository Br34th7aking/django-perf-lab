from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Comment, Post


class Health(APIView):
    def get(self, request):
        return Response({
            "status": "ok",
            "posts": Post.objects.count(),
            "comments": Comment.objects.count(),
        })