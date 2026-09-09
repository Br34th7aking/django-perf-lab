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