# django-perf-lab

Mini-labs reproducing common Django/DRF performance problems — each one measured
broken, fixed, and measured again. Stack: Django 5 · DRF · Postgres 17 · Redis 7 ·
gunicorn, all in docker compose. Profiling: django-silk. Load testing: locust.

## Run

    docker compose up -d
    docker compose exec web python manage.py migrate
    docker compose exec web python manage.py seed   # 100k posts, 500k comments

Every lab keeps both endpoints live: `/labs/NN/bad/` and `/labs/NN/good/`.

## Findings

| Lab | Problem | Before | After | Fix |
|-----|---------|--------|-------|-----|
| [01](#lab-01--n1-queries) | N+1 queries | 61 queries / 59 ms | 2 queries / 34 ms | `select_related` + `prefetch_related` |
| [02](#lab-02--indexing) | Seq scan on unindexed filter | 28 ms | 0.18 ms | `db_index=True` + migration |
| [03](#lab-03--counts) | Paying for counts nobody needs | 27 ms | ~1 ms | `exists()` / skip or estimate the count |
| [04](#lab-04--payload-trimming) | Fetching 2 KB bodies to show titles | 333 ms / 14.7 MB | 9 ms / 0.7 MB | `only()` / `values_list()` |
| [05](#lab-05--unbounded-queries) | List endpoint with no pagination | 22 s median @ 10 users | 29 ms median | paginate |
| [06](#lab-06--memoization) | Query method called 4× per request | 9 queries / 82 ms | 3 queries / 21 ms | `@cached_property` |
| [07](#lab-07--generic-foreign-keys) | GenericForeignKey where a concrete FK would do | 60 ms / 51 queries | 10 ms / 2 queries | concrete FK (or composite index + prefetch) |
| [08](#lab-08--orm-query-cache) | Recomputing identical reads | 33 ms/req | 7 ms/req | django-cachalot — with a process-level staleness boundary |
| [09](#lab-09--raw-sql) | Double to-many `annotate(Count)` | 9,346 ms | 32 ms | correlated subqueries via raw SQL |
| [10](#lab-10--denormalization) | Aggregate recomputed per read | 406 ms | 26 ms | `comment_count` column, maintained on write (+79% write cost) |

### Lab 01 — N+1 queries

Listing 20 posts with author, category, and tags: the serializer touches lazy
relations per post, so 1 query becomes 1 + 3×20 = **61**. `select_related`
JOINs the to-one relations (author, category) into the main query;
`prefetch_related` batches the M2M tags into one extra query — **2 total**,
constant in page size.

The trap: calling `.filter()` on a prefetched relation silently ignores the
prefetch and queries per post again (22 queries). Fix: push the filter into
`Prefetch(queryset=...)` — back to 2.

| Endpoint | Queries | Time |
|----------|---------|------|
| `/labs/01/bad/` | 61 | 59 ms |
| `/labs/01/good/` | 2 | 34 ms |
| `/labs/01/trap/` | 22 | 58 ms |
| `/labs/01/trap-fixed/` | 2 | 22 ms |

Locked in by `labs/test_lab01.py`: the good endpoints are pinned at 2 queries,
so a regression fails CI. Measured via silk, seeded DB (100k posts / 500k
comments), local docker.

### Lab 02 — Indexing

Filtering 100k posts to a one-week window (~2k rows) on an unindexed date
column forces a full-table read. Two mirror columns with identical data isolate
the variable: `published_on` (no index) vs `published_on_idx` (indexed).

Before — Seq Scan reads all 100k rows, then sorts:

    Limit (actual time=28.041..28.045 rows=50)
      -> Sort (actual time=28.040..28.041 rows=50)
         -> Seq Scan on core_post (actual time=10.299..27.850 rows=2003)
    Execution Time: 28.080 ms

After `db_index=True` + migration — Index Scan, pre-sorted, stops at 50 rows:

    Limit (actual time=0.020..0.157 rows=50)
      -> Index Scan using core_post_published_on_idx (actual time=0.020..0.154 rows=50)
    Execution Time: 0.182 ms

Three lessons beyond the 150× headline:

1. **The planner decides, not you.** The same index is used three ways
   depending on how many table pages the query must touch: `count(*)` on a
   6-month window → Index Only Scan (touches zero pages, 3.5 ms);
   `avg(length(title))` on the same window → Seq Scan (50k scattered heap
   visits would cost more than reading everything).
2. **Writes pay for reads.** 20k inserts: 120 ms with the index, 82 ms
   without (measured via transactional DROP INDEX + ROLLBACK). One date
   index ≈ +46% insert time. Indexes are a per-write tax, so they must earn
   their keep.
3. **The classic miss:** `db_index=True` changes nothing until the migration
   runs. `labs/test_lab02.py` pins the index's existence via schema
   introspection so CI catches a missing migration.

| Endpoint | Column | Plan | Time |
|----------|--------|------|------|
| `/labs/02/bad/` | `published_on` | Seq Scan + Sort | 28 ms |
| `/labs/02/good/` | `published_on_idx` | Index Scan | 0.18 ms |

### Lab 03 — Counts

Counting is a full pass over matching rows. Three disguises of the same
mistake — paying for exactness nobody asked for:

1. **Existence:** `count() > 0` tallies all 500k comments to answer a yes/no
   question; `exists()` compiles to `SELECT 1 ... LIMIT 1` and stops at the
   first row. 27 ms → ~1 ms.
2. **Pagination:** DRF's `PageNumberPagination` fires `SELECT COUNT(*)` on
   every page request just to report the total. A paginator with a stubbed
   count keeps next/previous navigation and drops the count query:
   2 queries / 8 ms → 1 query / 2 ms. Trade-off: no real total — which most
   infinite-scroll UIs never displayed anyway.
3. **Dashboard totals:** `pg_class.reltuples` (the planner's own estimate,
   maintained by autovacuum) answers "how many posts?" from the catalog —
   no table access at all: 22 ms → 8 ms request time, zero ORM queries.
   Trade-off: staleness between autovacuum passes, and per-table only (no
   filtered estimates).

The staleness trade-off demonstrated itself: mid-lab, the exact count said
140,000 while the estimate said 104,946 — the estimate was "wrong" but the
table had quietly gained 40k rows from a leaked experiment. Every count over
a busy table is stale by the time it renders; the question is never "how do
I count fast?" but "how stale a number can this screen tolerate?"

Production systems answer that question visibly once you look: Google's
"about 1,240,000 results", GitHub capping issue counts at "5,000+", admin
dashboards showing "~2.3M users", view counters that update in lurches.
Each is some flavor of the above — an estimate, a cached count refreshed on
a schedule, or a denormalized counter (Lab 10's topic). An invoice tolerates
zero staleness; a results header tolerates almost anything.

| Endpoint | Queries | Time |
|----------|---------|------|
| `/labs/03/bad/` (`count() > 0`) | 1 (COUNT) | 27 ms in SQL |
| `/labs/03/good/` (`exists()`) | 1 (LIMIT 1) | ~1 ms in SQL |
| `/labs/03/page-counted/` | 2 | 8 ms |
| `/labs/03/page-nocount/` | 1 | 2 ms |
| `/labs/03/count-exact/` | 1 | 22 ms request |
| `/labs/03/count-approx/` | 0 | 8 ms request |

`labs/test_lab03.py` pins the SQL shape: the good existence check must
contain `LIMIT 1` and no `COUNT`; no-count pagination must run exactly one
query.

### Lab 04 — Payload trimming

Collecting 5,000 post titles, three ways. Endpoints self-measure with
`tracemalloc` + `perf_counter` (absolute times inflated by tracing; the
comparison is fair):

| Endpoint | Fetches | Time | Peak memory |
|----------|---------|------|-------------|
| `/labs/04/full/` | whole rows, model objects | 333 ms | 14.65 MB |
| `/labs/04/only/` | 2 columns, model objects | 66 ms | 2.18 MB |
| `/labs/04/values/` | 1 column, plain tuples | 9 ms | 0.70 MB |

The two gaps are two different costs. `full → only` is **data movement**:
5,000 × ~2 KB bodies that stopped leaving postgres (−12.5 MB, −267 ms).
`only → values` is **object construction**: 5,000 Django model `__init__`s
skipped — each instance carries a `__dict__` and field state, and
instantiation dominates the remaining time (−1.5 MB, −57 ms). Rule: pay for
model objects only when you'll call their methods; for read-only projection,
ship tuples.

The trap (`/labs/04/defer-trap/`): `defer("body")` hands back objects with a
hole in them — *touching* `.body` silently refetches it, one query per
object (21 queries for 20 posts). N+1 with no relation in sight: `defer` is
a bet you won't touch what you skipped. `labs/test_lab04.py` pins the column
lists in the SQL and the trap's per-row cost.

### Lab 05 — Unbounded queries

A list endpoint without pagination returns the whole table. It works fine in
development with 50 rows, then the table grows. At 100k posts, one request
to `/labs/05/bad/` builds an 11 MB response in 2.3 seconds. The paginated
version returns 2 KB in 15 ms.

The single-request cost is not the real problem. The real problem shows up
under load — 10 concurrent users for 60 seconds (locust, 1 gunicorn worker):

| | `/labs/05/bad/` | `/labs/05/good/` |
|---|---|---|
| Requests completed | 25 | 374 |
| Throughput | 0.43 req/s | 6.26 req/s |
| Median latency | 22,000 ms | 29 ms |
| Single-user latency | 2,300 ms | 15 ms |

The worker serves one request at a time. When each takes 2.3 s, arriving
requests wait in line, and the line grows faster than it drains: a 2.3 s
endpoint becomes a 22 s endpoint at 10 users. The paginated endpoint's
median under load (29 ms) is the same as its single-user cost — its latency
does not depend on how many people are asking.

That is the definition of stable vs collapsing: not how slow one request is,
but whether latency is a function of load. A side effect worth noting: the
first requests after the bad run also measured slow — the unbounded endpoint
was still draining and blocked the worker for everyone. One unbounded
endpoint degrades every endpoint that shares its worker.

`labs/test_lab05.py` pins the contract: the bad response grows with the
table, the good one stays at 20 rows regardless.

### Lab 06 — Memoization

`Post.comment_stats()` runs two queries. Four response fields each call it,
because in real code the callers never see each other — one lives in a
serializer field, another in a template fragment, another in a helper. Each
call pays again: 1 + 4×2 = **9 queries / 82 ms** per request.

`@cached_property` computes on first access and stores the result on the
instance; every later access reads the stored value. Same four callers,
**3 queries / 21 ms** — and the callers didn't change, only the decorator.

This cache is safe because its lifetime equals the object's lifetime, and
the `Post` instance lives for exactly one request. The next request builds
a fresh instance with an empty cache, so it can never serve stale data
across requests. Most caching bugs are invalidation bugs; here invalidation
is garbage collection.

| Endpoint | Queries | Time |
|----------|---------|------|
| `/labs/06/bad/<pk>/` | 9 | 82 ms |
| `/labs/06/good/<pk>/` | 3 | 21 ms |

`labs/test_lab06.py` pins both query counts and asserts the two endpoints
return identical payloads — the optimization changed cost, not behavior.

### Lab 07 — Generic foreign keys

A `GenericForeignKey` stores its target as two loose columns —
`content_type_id` (which table) and `object_id` (which row) — so one `Like`
table can point at any model. The database no longer understands the
relationship: no FK constraint, no automatic index on `object_id`, no single
join target. Setup: 200k likes stored twice, as generic `Like` rows and as
concrete `PostLike` rows with a plain FK, identical distribution.

Counting likes for a 20-post page, one query each way:

| Endpoint | Join strategy (EXPLAIN) | Time |
|----------|------------------------|------|
| `/labs/07/bad/` (generic) | Seq scan all 200k likes → hash join → on-disk sort | 60 ms |
| `/labs/07/good/` (concrete) | Nested loop: index lookup per post, touches only the page's likes | 10 ms |

The concrete query's cost scales with page size; the generic one scales with
total likes ever recorded, because `object_id` has no index and the compound
join condition rules out the simple plan. A composite index on
`(content_type, object_id)` mitigates this, but concrete FKs ship the index
by default.

Resolving `like.content_object` has no join at all — row 1 may live in the
posts table, row 2 in comments — so the ORM fetches lazily, one query per
row: the 50-like feed runs 51 queries. `prefetch_related("content_object")`
batches one fetch per distinct content type (2 queries here). The query
count still scales with the number of types on the page, where a concrete
FK is always a single JOIN.

| Endpoint | Queries | Time |
|----------|---------|------|
| `/labs/07/feed/` | 51 | 36 ms |
| `/labs/07/feed-fixed/` | 2 | 8 ms |

GFK buys schema flexibility with integrity and index support. It fits
genuinely open-ended targets (audit logs, notifications, tags-on-anything).
With exactly one target model, the concrete FK is faster on aggregates,
immune to the resolution explosion, and enforced by the database.
`labs/test_lab07.py` pins the explosion arithmetic and that both count
endpoints return identical payloads.

### Lab 08 — ORM query cache

django-cachalot caches every queryset result in Redis, keyed by the SQL,
and invalidates all cached queries for a table whenever that table is
written. Workload: Lab 7's 33 ms like-count aggregate.

| Step | Time |
|------|------|
| Uncached, every request | 33 ms |
| Cache miss (computes + stores) | 34 ms |
| Cache hit | 7 ms |
| After ORM write to `core_like` | 34 ms (invalidated), then 7 ms |

Invalidation reaches further than expected: raw SQL through Django's cursor
is also caught — cachalot patches the cursor and parses statements for
table names. The boundary is the *process*, not the API. A write from
outside — psql in this experiment, in production an ETL job, another
service, or a management command running under settings without cachalot —
invalidates nothing: after an external INSERT, the cache served like-count
631 in 10 ms while the database held 632, and stayed wrong until the next
in-process write or TTL expiry (300 s default).

Table-level granularity sets the profile narrowly: one write to a table
evicts every cached query touching it, so write-active tables thrash the
cache and pay Redis round-trips for nothing. Postgres has no query cache
and MySQL removed theirs in 8.0 for exactly this invalidation-churn reason.
Transparent query caching fits read-heavy, rarely-written tables — content,
catalogs, configuration — and cachalot can be scoped to just those via
settings. For everything else, explicit caching with chosen keys and TTLs
(labs 14–16) keeps the staleness trade-off visible in the code.

`labs/test_lab08.py` pins payload equality between cached and uncached
paths and both write endpoints' effects (cachalot stays out of test
settings, so tests always compute).

### Lab 09 — Raw SQL

Task: 20 posts with their comment count and like count. The ORM's natural
spelling joins both to-many tables at once, and a SQL join of two to-many
relations produces the cross-product — every comment paired with every
like:

    Post.objects.annotate(comment_count=Count("comments"),
                          like_count=Count("likes"))

| Endpoint | Result | Time |
|----------|--------|------|
| `/labs/09/wrong/` | both counts = comments × likes (17,845,380 for a 28,326-comment, 630-like post) | 3,502 ms |
| `/labs/09/bad/` — `Count(..., distinct=True)` | correct | 9,346 ms |
| `/labs/09/good/` — raw SQL | correct | 32 ms |

`distinct=True` restores correctness but not the plan: the join still
materializes ~18M rows for the heavy post, then pays de-duplication on top.
The raw rewrite replaces join-then-group with two correlated subqueries —
each of the 20 posts runs two small indexed counts, so the work scales with
the page's own rows, never a product:

    SELECT p.id, p.title,
           (SELECT count(*) FROM core_comment c WHERE c.post_id = p.id),
           (SELECT count(*) FROM core_postlike l WHERE l.post_id = p.id)
      FROM core_post p ORDER BY p.id LIMIT 20

What raw SQL gives up: queryset composability (no further `.filter()`),
portability across databases, and the ORM's parameter handling unless
placeholders are used rigorously. The same plan is reachable inside the ORM
with `Subquery(...)` annotations — clumsier to read, but it keeps
composability; raw SQL is the escape hatch, not the first resort.

### Lab 10 — Denormalization

"Top 20 most-commented posts" computed per read must count 500k comments
and group 100k posts before it can sort. Storing the answer — a
`comment_count` column on `Post`, incremented and decremented by
`post_save`/`post_delete` signal receivers using `F()` expressions (atomic
in the database, no read-modify-write race) — turns the read into an
ORDER BY + LIMIT.

| Operation | Computed | Stored column |
|-----------|----------|---------------|
| Read: top-20 by comment count | 406 ms | 26 ms |
| Write: 1,000 comment inserts | 523 ms | 936 ms (+79%) |
| Rebuild counter from truth | — | 1.25 s (full recount) |

The read win is paid for on every write: each comment insert now runs two
statements, its own INSERT plus the post's UPDATE. Denormalization is a
bet that the read/write ratio is high enough to cover that tax — here,
one hot read per 15 writes already breaks even.

The counter is only as true as the code paths that maintain it.
`bulk_create` skips signals, so the seed command backfills with one UPDATE
afterwards — and `labs/test_lab10.py` pins the drift as documented
behavior. Any writer outside the maintenance path (raw SQL, another
service, an ETL) silently desynchronizes the column; the 1.25 s rebuild is
the recovery tool, cheap enough to run on a schedule.

Adding the column also broke lab 9: its `annotate(comment_count=...)`
collided with the new field name and Django raised `ValueError` at query
construction. A denormalized column claims a name application-wide — every
existing annotation of that name is in its blast radius.