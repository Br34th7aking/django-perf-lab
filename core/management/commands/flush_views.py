import os

import redis
from django.core.management.base import BaseCommand
from django.db.models import F

from core.models import Post


class Command(BaseCommand):
    help = "Flush pending view counts from redis into postgres"

    def handle(self, *args, **options):
        r = redis.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        )
        flushed = 0
        for key in r.scan_iter("post:*:pending_views"):
            delta = int(r.getdel(key) or 0)
            if not delta:
                continue
            pk = int(key.decode().split(":")[1])
            Post.objects.filter(pk=pk).update(view_count=F("view_count") + delta)
            flushed += 1
            self.stdout.write(f"post {pk}: +{delta}")
        self.stdout.write(self.style.SUCCESS(f"flushed {flushed} counters"))