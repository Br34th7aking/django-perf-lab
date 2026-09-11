from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Tag


class ReadYourWrites(APIView):
    """Write, then immediately read it back the way normal code would."""

    def get(self, request):
        tag = Tag.objects.create(name="anomaly-probe")          # -> primary
        pk = tag.pk
        via_replica = Tag.objects.filter(pk=pk).exists()         # -> replica
        via_primary = Tag.objects.using("default").filter(pk=pk).exists()
        tag.delete()
        return Response({
            "written_pk": pk,
            "immediately_visible_via_normal_read_path": via_replica,
            "immediately_visible_on_primary": via_primary,
        })
