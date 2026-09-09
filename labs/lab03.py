from django.core.paginator import Paginator
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Comment, Post


class HasCommentsBad(APIView):
    def get(self, request):
        has_comments = Comment.objects.count() > 0
        return Response({"has_comments": has_comments})


class HasCommentsGood(APIView):
    def get(self, request):
        has_comments = Comment.objects.exists()
        return Response({"has_comments"})


class PostTitleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ["id", "title"]


class CountedPagination(PageNumberPagination):
    page_size = 20


class FakeCountPaginator(Paginator):
    @property
    def count(self):
        return 10**9


class NoCountPagination(PageNumberPagination):
    page_size = 20
    django_paginator_class = FakeCountPaginator


class PostsPageCounted(ListAPIView):
    serializer_class = PostTitleSerializer
    pagination_class = CountedPagination
    queryset = Post.objects.order_by("id")


class PostsPageNoCount(ListAPIView):
    serializer_class = PostTitleSerializer
    pagination_class = NoCountPagination
    queryset = Post.objects.order_by("id")