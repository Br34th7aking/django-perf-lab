# django-perf-lab — Master Plan

One repo, ~21 mini-labs. Each lab reproduces one Django/DRF performance problem, fixes it, and proves the fix with numbers. Ends with a meaty integration project. This file is the single source of truth — any session (human or Claude) starts by reading it and the **STATE** section at the bottom.

## How to use this file (instructions for Claude)

- Read this whole file first, then read STATE at the bottom to see where we are.
- Work one lab at a time. When a lab completes, update STATE + tick its checkbox, then immediately point to the next lab.
- STATE in this file is the canonical progress tracker — do not rely on anything else.

## Working agreements (non-negotiable)

1. **The user types all code themselves** in their terminal. Claude gives exact, complete instructions (full file paths, full snippets) and waits. Claude edits files directly only when explicitly asked (e.g. fixing a typo).
2. **Explicit go before building.** Discussing or answering questions ≠ approval to start. The user says when discussion ends.
3. **Short responses, one idea at a time.** No walls of text, no unexplained jargon. Depth on request.
4. **Debugging**: when asked, Claude may run read-only checks (curl, logs, docker ps) directly. Layered diagnosis — unfiltered output before filtered.
5. **Verify user-visible outcomes.** A step is done when the endpoint/measurement actually works, not when the code looks right.
6. **No outward actions** (push, publish, merge) by Claude — the user commits and pushes. Commit style: conventional commits (`type: subject`), no Co-Authored-By trailers.
7. **Independent work framing**: no references to any book or course anywhere in this repo (README, code comments, notes). The concepts stand on their own.
8. One lab ≈ one sitting. Keep it game-shaped: build, measure, win, next.

## Locked decisions

| Area | Choice |
|---|---|
| Language/framework | Python 3.13 · Django 5.x · **DRF** (API-first; templates only where a lab demands it) |
| DB / cache | postgres:17-alpine · redis:7-alpine · `psycopg[binary]` |
| Serving | gunicorn in docker compose (dev-parity rule: local = prod shape) |
| Profiling | **django-silk** (dev-only) + `assertNumQueries` in tests |
| Load testing | **locust** (wrk optional for quick raw ceilings) |
| ORM query cache | django-cachalot |
| Async | Celery, broker = Redis |
| Feature flags | django-waffle |
| CI | GitHub Actions: pytest + pytest-django + coverage + ruff |
| Settings | `settings/` package: `base.py` / `deploy.py` / `local.py` (uncommitted, `local.py.example` committed) |

## Repo layout (target)

```
django-perf-lab/
├── PLAN.md              ← this file
├── README.md            ← the deliverable: findings + numbers per lab
├── docker-compose.yml   ← web (gunicorn), db, redis, worker (from Arc D)
├── Dockerfile
├── core/                ← shared models + seed command
├── labs/                ← one views module per lab: lab01.py, lab02.py …
│   └── urls: /labs/NN/bad/ and /labs/NN/good/  (both stay live — demos)
├── locustfiles/
└── .github/workflows/ci.yml
```

## Shared domain (built once, Lab 0)

Blog-shaped — chosen because it naturally exercises every lab:

- `Author` (~1,000) · `Category` (20) · `Tag` (50)
- `Post` (~100,000): FK author, FK category, M2M tags, `title`, `body` ≈ 2 KB text, `created_at`, `last_modified` (auto_now)
- `Comment` (~300,000): FK post, body — skewed so some posts have thousands
- `Like` (Lab 7 adds it): GenericForeignKey
- `python manage.py seed` — bulk_create, batched, idempotent (wipes + reseeds)

## Lab format (every lab)

1. Build the **bad** endpoint → measure (silk: query count + time; locust where load matters)
2. Build the **good** endpoint (bad stays live) → re-measure
3. README entry: numbers table + 2–4 sentence finding
4. Definition of done: both endpoints respond, numbers recorded, README updated

---

## Lab 0 — Scaffold  *(the one-time cost; ~2 sittings)*

Compose stack up (web/db/redis) · settings package · models + seed · DRF + silk wired (`/silk/`) · locustfile skeleton · CI green on a trivial test · README skeleton with findings-table format.
**Done when:** `docker compose up` → seeded API responds, silk records a request, CI passes.

## Arc A — Query reduction

- [ ] **Lab 1 · N+1** — post list serializing author + category: watch ~2N+1 queries in silk → `select_related`; tags → `prefetch_related`. Also demo the trap: `.filter()` on a prefetched relation fires a new query (fix: filter in Python or `Prefetch`). **Prove:** 41+ queries → ~3.
- [ ] **Lab 2 · Indexing** — filter posts on an unindexed column @100k rows. `EXPLAIN` shows Seq Scan → `db_index=True` + migration → Index Scan. Note the caveats: verify the planner uses it; indexes cost every write; the classic miss is forgetting the migration. **Prove:** query-time drop, EXPLAIN before/after in README.
- [ ] **Lab 3 · Counts** — `count() > 0` vs `exists()`; pagination with vs without total count; approximate count via `pg_class.reltuples`. **Prove:** timing table for all three.
- [ ] **Lab 4 · Payload trimming** — full model fetch vs `defer('body')` / `only()` vs `values()` / `values_list()` on the 2 KB-body posts. **Prove:** time + memory difference; note values/values_list skip model init entirely.
- [ ] **Lab 5 · Unbounded queries** — `.all()` list endpoint vs paginated, under locust. **Prove:** latency/throughput collapse vs stable.
- [ ] **Lab 6 · Memoization** — model method doing queries, called 5× per request → `@cached_property`. **Prove:** query count drops; explain why request-scoped cache can never go stale.
- [ ] **Lab 7 · Generic FK cost** — add `Like` via contenttypes; list posts with like info vs a concrete-FK equivalent. **Prove:** the query explosion, measured.

## Arc B — Beyond the ORM

- [ ] **Lab 8 · ORM query cache** — django-cachalot on/off; show a table write invalidating that table's cached queries; show the trap: scripts/management commands bypassing invalidation unless enabled. **Prove:** repeat-request time with/without cachalot.
- [ ] **Lab 9 · Raw SQL** — one aggregate the ORM produces badly; rewrite with `raw()`/custom SQL. **Prove:** query plans + timings side by side; note what you give up (portability, safety of composition).
- [ ] **Lab 10 · Denormalization** — `comment_count` column maintained on write vs `annotate(Count(...))` per read. **Prove:** read win AND the doubled-write/sync cost, both measured.
- [ ] **Lab 11 · Read replica** — second postgres in compose + streaming replication + Django DB router (reads→replica). **Prove:** routing works; demo replication lag / read-your-writes anomaly.
- [ ] **Lab 12 · Redis complement** — post view-counter: UPDATE-per-hit in postgres vs Redis INCR (periodic flush). **Prove:** throughput under locust.
- [ ] **Lab 13 · Search** — `icontains` vs Postgres full-text (`SearchVector` + GIN index). Elasticsearch = optional stretch, not required. **Prove:** timings @100k rows.

## Arc C — Caching

- [ ] **Lab 14 · Response caching** — cache the rendered API response (per-view / low-TTL) vs recompute. **Prove:** silk + locust before/after; echoes the serve-from-as-high-up-as-possible principle.
- [ ] **Lab 15 · Russian doll** — one template-rendered page (the exception to API-first): nested `{% cache %}`, short-TTL outer ⊃ long-TTL inner keyed on `post.last_modified`. Edit one post → only that fragment re-renders. Add magic `?flush` param. **Prove:** render times: cold / warm / one-fragment-stale.
- [ ] **Lab 16 · Thundering herd** — many keys with identical TTL expiring together under locust → load spike; fix with ±20% jitter. **Prove:** the spike graph flattens.

## Arc D — Async (adds `worker` service to compose)

- [ ] **Lab 17 · Celery offload** — view doing slow work (simulated email/API call) sync vs `.delay()`. **Prove:** p95 latency before/after under locust.
- [ ] **Lab 18 · on_commit race** — create object + queue task inside a transaction → intermittent DoesNotExist; fix with `transaction.on_commit`. **Prove:** reproduce the failure, then zero failures.
- [ ] **Lab 19 · Priority queues** — two queues; flood low-priority; high-priority tasks still picked up instantly. **Prove:** task wait-time comparison.
- [ ] **Lab 20 · Celery beat** — scheduled cleanup task (e.g. purge stale rows) vs cron; note retries + monitoring advantages. **Prove:** it fires on schedule, visibly.

## Arc E — Rollout

- [ ] **Lab 21 · Feature flags** — django-waffle: percentage rollout of a new endpoint variant + `/api/flags/` for JS clients; note cookie-stickiness caveat for tokened API clients (target by user/group instead). **Prove:** ~10% of sessions get the variant.

---

## Milestones

- [ ] **M0** — Lab 0 done: stack up, seeded, silk live, CI green
- [ ] **M1** — Arc A done (labs 1–7): README "Query reduction" section, every lab with numbers
- [ ] **M2** — Arc B done (labs 8–13)
- [ ] **M3** — Arc C done (labs 14–16)
- [ ] **M4** — Arc D done (labs 17–20): worker + beat in compose
- [ ] **M5** — Arc E + polish: README opens with a summary table of all findings. Decision point (user's call): make repo public / pin on GitHub.
- [ ] **M6** — Meaty project: scope it fresh when M5 lands (see below). Gated on explicit go.

## Meaty project (scope at M6, not before)

A real DRF + React app where the techniques appear in context instead of isolation. Natural home for the topics that aren't lab-shaped: static pipeline (bundling/versioning), image optimization, CDN/WhiteNoise, S3-style uploads with Celery thumbnail pre-generation + on-the-fly fallback, full CI. Whether this is a new app or folded into an existing project is the user's decision at M6. Skipped permanently: sharding (demo adds nothing).

---

## STATE  *(update after every sitting)*

- **Last updated:** 2026-09-04
- **Where we are:** Plan written. Nothing built. Repo not yet git-initialized.
- **Next action:** Lab 0 — scaffold. Start with git init + Dockerfile/compose (pattern user already knows), then settings package, then models + seed.
- **Session log:**
  - 2026-09-04 — plan created.
