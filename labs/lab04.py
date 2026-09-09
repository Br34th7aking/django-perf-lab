import time
import tracemalloc

from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Post

N = 5000


def measured(fn):
    tracemalloc.start()
    t0 = time.perf_counter()
    result = fn()
    ms = (time.perf_counter() - t0) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"rows": len(result), "ms": round(ms, 1), "peak_mb": round(peak / 1e6, 2)}


class TitlesFull(APIView):
    """
    Fetches complete rows - builds full model objects.
    """
    
    def get(self, request):
        return Response(measured(lambda: [p.title for p in Post.objects.all()[:N]]))
    

class TitlesOnly(APIView):
    """
    only('title'): model objects, but just two columns leave postgres.
    """
    def get(self, request):
        return Response(measured(lambda: [p.title for p in Post.objects.only("title")[:N]]))


class TitlesValues(APIView):
    """
    values_list: no model objects at all - raw strings straight from the cursor.
    """

    def get(self, request):
        return Response(measured(lambda: list(Post.objects.values_list("title", flat=True)[:N])))
        

