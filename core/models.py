import uuid

from django.db import models
from django.utils.functional import cached_property


class TimestampedModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True



class Author(TimestampedModel):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Category(TimestampedModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Tag(TimestampedModel):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Post(TimestampedModel):
    title = models.CharField(max_length=200)
    body = models.TextField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="posts")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="posts")
    tags = models.ManyToManyField(Tag, related_name="posts")
    published_on = models.DateTimeField(null=True) # unindexed, bad
    published_on_idx = models.DateTimeField(null=True, db_index=True) # indexed

    def __str__(self):
        return self.title[:80]

    def comment_stats(self):
        """Two queries every single cell"""
        latest = self.comments.order_by("-created_at").first()
        return {
            "count": self.comments.count(),
            "latest": latest.body[:50] if latest else None,
        }
    
    @cached_property
    def comment_stats_cached(self):
        """Same two queries but fired only on first access each instance."""
        latest = self.comments.order_by("-created_at").first()
        return {
            "count": self.comments.count(),
            "latest": latest.body[:50] if latest else None,
        }


class Comment(TimestampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()

    def __str__(self):
        return f"Comment on {self.post_id}"
