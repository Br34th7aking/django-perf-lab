from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.shortcuts import render

from core.models import Post


def page_bad(request):
    posts = Post.objects.select_related("author").order_by("-id")[:50]
    return render(request, "labs/lab15_bad.html", {"posts": posts})


def page_good(request):
    posts = Post.objects.select_related("author").order_by("-id")[:50]
    if "flush" in request.GET:
        cache.delete(make_template_fragment_key("lab15_page"))
        for post in posts:
            cache.delete(make_template_fragment_key("lab15_post", [post.pk, post.last_modified]))
    
    return render(request, "labs/lab15_good.html", {"posts": posts})