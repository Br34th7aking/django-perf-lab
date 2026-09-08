from django.db.models import Prefetch
from rest_framework import serializers
from rest_framework.generics import ListAPIView

from core.models import Post, Tag


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



class PostListGood(ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        return (
            Post.objects.select_related("author", "category")
            .prefetch_related("tags")
            .order_by("-created_at")[:20]
        )


class TrapSerializer(serializers.ModelSerializer):
    matching_tags = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["id", "title", "matching_tags"]

    def get_matching_tags(self, post):
        return [t.name for t in post.tags.filter(name__startswith="tag-1")]


class TrapFixedSerializer(serializers.ModelSerializer):
    matching_tags = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ["id", "title", "matching_tags"]
    

    def get_matching_tags(self, post):
        return [t.name for t in post.matching] # filled by Prefetch(to_attr=...)


class PostListTrap(ListAPIView):
    serializer_class = TrapSerializer

    def get_queryset(self):
        return Post.objects.prefetch_related("tags").order_by("-created_at")[:20]


class PostListTrapFixed(ListAPIView):
    serializer_class = TrapFixedSerializer

    def get_queryset(self):
        return Post.objects.prefetch_related(
            Prefetch(
                "tags",
                queryset=Tag.objects.filter(name__startswith="tag-1"),
                to_attr="matching",
            )
        ).order_by("-created_at")[:20]

