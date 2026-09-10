import random
import time

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import connection

from core.models import Author, Category, Comment, Like, Post, PostLike, Tag

WORDS = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore", "magna", "aliqua", "enim", "ad", "minim", "veniam", "quis", "nostrud", "exercitation", "ullamco", "laboris", "nisi", "aliquip", "ex", "ea", "commodo", "consequat", "duis", "aute", "irure", "in", "reprehenderit", "voluptate", "velit", "esse", "cillum"]


N_AUTHORS = 1000
N_CATEGORIES = 20
N_TAGS = 50
N_POSTS = 100000
N_COMMENTS = 500000
CHUNK = 5000


def text(n_words):
    return " ".join(random.choices(WORDS, k=n_words))


class Command(BaseCommand):
    help = "Wipe and reseed all test data(idempotent)"

    def handle(self, *args, **options):
        t0 = time.monotonic()

        tables = [
            Like._meta.db_table,
            PostLike._meta.db_table,
            Comment._meta.db_table,
            Post.tags.through._meta.db_table,
            Post._meta.db_table,
            Tag._meta.db_table,
            Category._meta.db_table,
            Author._meta.db_table,
        ]
        with connection.cursor() as cur:
            cur.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")
        self.stdout.write("wiped")
        
        Author.objects.bulk_create(
        [Author(name=f"Author {i}") for i in range(N_AUTHORS)], batch_size=1000
        )
        Category.objects.bulk_create(
        [Category(name=f"Category {i}") for i in range(N_CATEGORIES)], batch_size=1000
        )
        Tag.objects.bulk_create(
        [Tag(name=f"tag-{i}") for i in range(N_TAGS)]
        )
        
        author_ids = list(Author.objects.values_list("id", flat=True))
        category_ids = list(Category.objects.values_list("id", flat=True))
        tag_ids = list(Tag.objects.values_list("id", flat=True))

        for start in range(0, N_POSTS, CHUNK):
            Post.objects.bulk_create(
                [
                    Post(
                        title=f"Post {i}: {text(5)}",
                        body=text(300),
                        author_id=random.choice(author_ids),
                        category_id=random.choice(category_ids),
                    )
                    for i in range(start, min(start + CHUNK, N_POSTS))
                ],
                batch_size=1000,
            )
            self.stdout.write(f"posts {min(start + CHUNK, N_POSTS)}/{N_POSTS}")
        
        post_ids = list(Post.objects.values_list("id", flat=True))

        PostTag = Post.tags.through
        PostTag.objects.bulk_create(
            [
                PostTag(post_id=pid, tag_id=tid)
                for pid in post_ids
                for tid in random.sample(tag_ids, k=random.randint(1, 3))
            ],
            batch_size=5000,
        )
        self.stdout.write("tags linked")

        n = len(post_ids)
        for start in range(0, N_COMMENTS, CHUNK):
            Comment.objects.bulk_create(
                [
                    Comment(
                        post_id=post_ids[int((n-1) * random.random() ** 4)],
                        body=text(30),
                    )
                    for _ in range(min(CHUNK, N_COMMENTS - start))
                ],
                batch_size=1000,
            )
            self.stdout.write(f"comments {min(start + CHUNK, N_COMMENTS)}/{N_COMMENTS}")

        post_ct = ContentType.objects.get_for_model(Post)
        N_LIKES = 200000
        liked = [post_ids[int((n-1) * random.random() **2)] for _ in range(N_LIKES)]
        for start in range(0, N_LIKES, CHUNK):
            chunk = liked[start:start+CHUNK]
            Like.objects.bulk_create(
                [Like(content_type=post_ct, object_id=pid) for pid in chunk],
                batch_size=1000,
            )
            PostLike.objects.bulk_create(
                [PostLike(post_id=pid) for pid in chunk], batch_size=1000
            )
            self.stdout.write(f"likes {min(start + CHUNK, N_LIKES)}/{N_LIKES}")
        with connection.cursor() as cur:
            cur.execute(
                f"UPDATE {Post._meta.db_table} "
                "SET created_at = now() - random() * interval '365 days'"
            )
            cur.execute(
                f"UPDATE {Post._meta.db_table} "
                "SET published_on = created_at::date, published_on_idx = created_at::date"
            )
        
        self.stdout.write(self.style.SUCCESS(f"done in {time.monotonic() - t0:.0f}s"))

