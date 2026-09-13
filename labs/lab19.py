import time

from rest_framework.decorators import api_view
from rest_framework.response import Response

from labs.tasks import bulk_task, urgent_task


@api_view(["POST"])
def flood(request):
    queue = request.GET.get("queue", "celery")
    for _ in range(200):
        bulk_task.apply_async(args=[time.time()], queue=queue)
    return Response({"queued": 200, "queue": queue})


@api_view(["POST"])
def urgent(request):
    urgent_task.apply_async(args=[time.time()], queue="celery")
    return Response({"queued": "urgent"})
