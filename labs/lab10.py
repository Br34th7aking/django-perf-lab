from django.db.models import Count
from rest_framework import serializers
from rest_framework.generics import ListAPIView

from core.models import Post


class PostCountSerializer(serializers.ModelSerializer):
    comment_count = serializers.IntegerField()

    class Meta:
        model = Post
        fields = ["id", "title", "comment_count"]


class PostComputedCountSerializer(serializers.ModelSerializer):
    comment_count = serializers.IntegerField(source="computed_count")

    class Meta:
        model = Post
        fields = ["id", "title", "comment_count"]


class TopPostsComputed(ListAPIView):
    """Counts 500k comments, groups 100k posts, sorts — on every request."""

    serializer_class = PostComputedCountSerializer

    def get_queryset(self):
        return Post.objects.annotate(computed_count=Count("comments")).order_by(
            "-computed_count"
        )[:20]


class TopPostsStored(ListAPIView):
    """Reads the maintained column: an ORDER BY and a LIMIT."""

    serializer_class = PostCountSerializer

    def get_queryset(self):
        return Post.objects.order_by("-comment_count")[:20]
