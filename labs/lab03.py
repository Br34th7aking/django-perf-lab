from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Comment


class HasCommentsBad(APIView):
    def get(self, request):
        has_comments = Comment.objects.count() > 0
        return Response({"has_comments": has_comments})


class HasCommentsGood(APIView):
    def get(self, request):
        has_comments = Comment.objects.exists()
        return Response({"has_comments": has_comments})