import os
import time

import redis
from celery import shared_task

r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


@shared_task
def mark_comment_processed(comment_id):
    from core.models import Comment

    try:
        comment = Comment.objects.get(pk=comment_id)
    except Comment.DoesNotExist:
        r.incr("lab18:ghost")
        raise
    comment.body += " [processed]"
    comment.save(update_fields=["body"])
    r.incr("lab18:processed")
    return comment_id


@shared_task
def send_confirmation_email(subscriber_id):
    time.sleep(2)
    return subscriber_id