import os
import random
import time

import redis
from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response

from core.models import Comment

r = redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
TTL = 30


def _category_stats(category_id):
    return {
        "category": category_id,
        "comments": Comment.objects.filter(post__category_id=category_id).count(),
    }


@api_view(["GET"])
def stats_bad(request, category_id):
    key = f"lab16:bad:{category_id}"
    data = cache.get(key)
    if data is None:
        data = _category_stats(category_id)
        r.hincrby("lab16:recomputes:bad", int(time.time()), 1)
        cache.set(key, data, TTL)
    return Response(data)


@api_view(["GET"])
def stats_good(request, category_id):
    key = f"lab16:good:{category_id}"
    data = cache.get(key)
    if data is None:
        data = _category_stats(category_id)
        r.hincrby("lab16:recomputes:good", int(time.time()), 1)
        cache.set(key, data, TTL * random.uniform(0.8, 1.2))

    return Response(data)