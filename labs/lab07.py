from django.db.models import Count
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Like, Post


class PostLikesSerializer(serializers.ModelSerializer):
    like_count = serializers.IntegerField()

    class Meta:
        model = Post
        fields = ["id", "title", "like_count"]


class PostsGenericLikes(ListAPIView):
    """Join condition: object_id == post.id and content_type_id == <post ct>."""

    serializer_class = PostLikesSerializer

    def get_queryset(self):
        return Post.objects.annotate(like_count=Count("generic_likes")).order_by("id")[:20]


class PostsConcreteLikes(ListAPIView):
    """Join condition: post_id == post.id."""
    serializer_class = PostLikesSerializer

    def get_queryset(self):
        return Post.objects.annotate(like_count=Count("likes")).order_by("id")[:20]


class LikesFeed(APIView):
    """Resolving content_object lazily: one query per like."""

    def get(self, request):
        likes = Like.objects.order_by("-id")[:50]
        return Response([str(like.content_object) for like in likes])


class LikesFeedFixed(APIView):
    """prefetch_related batches resolution: one query per content type."""

    def get(self, request):
        likes = Like.objects.prefetch_related("content_object").order_by("-id")[:50]
        return Response([str(like.content_object) for like in likes])