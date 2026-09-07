from rest_framework import serializers
from rest_framework.generics import ListAPIView

from core.models import Post


class PostSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source="author.name")
    category = serializers.CharField(source="category.name")
    tags = serializers.SlugRelatedField(slug_field="name", many=True, read_only=True)

    class Meta:
        model = Post
        fields = ["id", "title", "author", "category", "tags", "created_at"]


class PostListBad(ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        return Post.objects.order_by("-created_at")[:20]

