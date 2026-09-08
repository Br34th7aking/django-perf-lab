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