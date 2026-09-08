from rest_framework import serializers
from rest_framework.generics import ListAPIView

from core.models import Post

WEEK = {"gte": "2026-06-01", "lt": "2026-06-08"}


class PostDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["id", "title", "published_on"]


class PostByDateBad(ListAPIView):
    serializer_class = PostDateSerializer

    def get_queryset(self):
        return Post.objects.filter(
            published_on__gte=WEEK["gte"], published_on__lte=WEEK["lt"]
        ).order_by("published_on")[:50]


class PostByDateGood(ListAPIView):
    serializer_class = PostDateSerializer

    def get_queryset(self):
        return Post.objects.filter(
            published_on_idx__gte=WEEK["gte"], published_on_idx__lte=WEEK["lt"]
        ).order_by("published_on_idx")[:50]