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