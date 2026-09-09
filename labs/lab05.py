from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from core.models import Post


class PostRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["id", "title", "created_at"]


class AllPosts(ListAPIView):
    """No pagination: serializes every row the table holds. """

    serializer_class = PostRowSerializer
    queryset = Post.objects.order_by("id")


class TwentyPerPage(PageNumberPagination):
    page_size = 20


class PagedPosts(ListAPIView):
    serializer_class = PostRowSerializer
    queryset = Post.objects.order_by("id")
    pagination_class = TwentyPerPage