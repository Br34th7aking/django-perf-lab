from django.db import models
import uuid

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

    def __str__(self):
        return self.title[:80]


class Comment(TimestampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    body = models.TextField()

    def __str__(self):
        return f"Comment on {self.post_id}"
