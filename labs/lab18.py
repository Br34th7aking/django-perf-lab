import time

from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Comment
from labs.tasks import mark_comment_processed


@api_view(["POST"])
def comment_bad(request):
    with transaction.atomic():
        comment = Comment.objects.create(post_id=1, body="lab18 race demo")
        mark_comment_processed.delay(comment.pk)
        time.sleep(0.05)
    return Response({"comment": comment.pk})


@api_view(["POST"])
def comment_good(request):
    with transaction.atomic():
        comment = Comment.objects.create(post_id=1, body="lab18 race demo")
        transaction.on_commit(lambda: mark_comment_processed.delay(comment.pk))
        time.sleep(0.05)
    return Response({"comment": comment.pk})


