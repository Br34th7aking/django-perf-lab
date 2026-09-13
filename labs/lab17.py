from rest_framework.decorators import api_view
from rest_framework.response import Response

from labs.tasks import send_confirmation_email


@api_view(["POST"])
def subscribe_bad(request):
    send_confirmation_email(1)
    return Response({"status": "subscribed"})


@api_view(["POST"])
def subscribe_good(request):
    result = send_confirmation_email.delay(1)
    return Response({"status": "accepted", "task_id": result.id})