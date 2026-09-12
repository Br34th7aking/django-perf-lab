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

- [x] **Lab 1 · N+1** — post list serializing author + category: watch ~2N+1 queries in silk → `select_related`; tags → `prefetch_related`. Also demo the trap: `.filter()` on a prefetched relation fires a new query (fix: filter in Python or `Prefetch`). **Prove:** 41+ queries → ~3. *(Done: 61→2 queries; trap 22→2; pinned by tests.)*
- [x] **Lab 2 · Indexing** — filter posts on an unindexed column @100k rows. `EXPLAIN` shows Seq Scan → `db_index=True` + migration → Index Scan. Note the caveats: verify the planner uses it; indexes cost every write; the classic miss is forgetting the migration. **Prove:** query-time drop, EXPLAIN before/after in README. *(Done: 28 ms → 0.18 ms; write tax +46%/20k inserts; index-only vs seq scan demo; index pinned by introspection test.)*
- [x] **Lab 3 · Counts** — `count() > 0` vs `exists()`; pagination with vs without total count; approximate count via `pg_class.reltuples`. **Prove:** timing table for all three. *(Done: exists 27→1 ms; pagination 2q/8ms→1q/2ms; approx count 22→8 ms with 0 queries; SQL-shape tests.)*
- [x] **Lab 4 · Payload trimming** — full model fetch vs `defer('body')` / `only()` vs `values()` / `values_list()` on the 2 KB-body posts. **Prove:** time + memory difference; note values/values_list skip model init entirely. *(Done: 333 ms/14.7 MB → 66 ms/2.2 MB → 9 ms/0.7 MB @5k titles; defer-touch trap = 21 queries; column lists pinned by tests.)*
- [x] **Lab 5 · Unbounded queries** — `.all()` list endpoint vs paginated, under locust. **Prove:** latency/throughput collapse vs stable. *(Done: 2.3 s solo → 22 s median @10 users vs flat 29 ms; 0.43 vs 6.26 req/s; queueing mechanism written up.)*
- [x] **Lab 6 · Memoization** — model method doing queries, called 5× per request → `@cached_property`. **Prove:** query count drops; explain why request-scoped cache can never go stale. *(Done: 9→3 queries, 82→21 ms; within-request mutation caveat documented; payload-equality test.)*
- [x] **Lab 7 · Generic FK cost** — add `Like` via contenttypes; list posts with like info vs a concrete-FK equivalent. **Prove:** the query explosion, measured. *(Done: aggregate 60→10 ms (seq-scan-all-likes vs indexed nested loop, EXPLAIN'd); feed 51→2 queries via GenericPrefetch; 200k mirrored likes in seed.)*

## Arc B — Beyond the ORM

- [x] **Lab 8 · ORM query cache** — django-cachalot on/off; show a table write invalidating that table's cached queries; show the trap: scripts/management commands bypassing invalidation unless enabled. **Prove:** repeat-request time with/without cachalot. *(Done: 33→7 ms; ORM + in-process raw SQL both invalidate (cursor patched — sharper than planned); external/psql writes don't → measured stale read. Narrow-profile verdict in README.)*
- [x] **Lab 9 · Raw SQL** — one aggregate the ORM produces badly; rewrite with `raw()`/custom SQL. **Prove:** query plans + timings side by side; note what you give up (portability, safety of composition). *(Done: double to-many Count = cross-product bug (3.5 s, wrong 630×) → distinct=True (9.3 s, correct) → correlated subqueries (32 ms). Subquery-annotation alternative noted.)*
- [x] **Lab 10 · Denormalization** — `comment_count` column maintained on write vs `annotate(Count(...))` per read. **Prove:** read win AND the doubled-write/sync cost, both measured. *(Done: read 406→26 ms; writes +79%; rebuild 1.25 s; bulk_create drift pinned by test; column name collision broke lab 9's annotations — fixed + documented.)*
- [x] **Lab 11 · Read replica** — second postgres in compose + streaming replication + Django DB router (reads→replica). **Prove:** routing works; demo replication lag / read-your-writes anomaly. *(Done: pg_basebackup + WAL streaming with 2 s apply delay; router splits reads/writes with zero app-code change; anomaly endpoint returns false/true deterministically.)*
- [x] **Lab 12 · Redis complement** — post view-counter: UPDATE-per-hit in postgres vs Redis INCR (periodic flush). **Prove:** throughput under locust. *(Done: store-level 2,637 vs 13,303 ops/s on hot row; 3,200 writes → 1; GETDEL flush lost nothing under load; 618 dead tuples as MVCC evidence. Locust HTTP layer muted by single worker — noted honestly.)*
- [x] **Lab 13 · Search** — `icontains` vs Postgres full-text (`SearchVector` + GIN index). Elasticsearch = optional stretch, not required. **Prove:** timings @100k rows. *(Done: 972–2,466 ms scans → 12–155 ms GIN; naive unindexed FTS slowest of all (4.8–17.8 s); generated column so no drift; ES skipped.)*

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

- [x] **M0** — Lab 0 done: stack up, seeded, silk live, CI green
- [x] **M1** — Arc A done (labs 1–7): README "Query reduction" section, every lab with numbers
- [x] **M2** — Arc B done (labs 8–13)
- [ ] **M3** — Arc C done (labs 14–16)
- [ ] **M4** — Arc D done (labs 17–20): worker + beat in compose
- [ ] **M5** — Arc E + polish: README opens with a summary table of all findings. Decision point (user's call): make repo public / pin on GitHub.
- [ ] **M6** — Meaty project: scope it fresh when M5 lands (see below). Gated on explicit go.

## Meaty project (scope at M6, not before)

A real DRF + React app where the techniques appear in context instead of isolation. Natural home for the topics that aren't lab-shaped: static pipeline (bundling/versioning), image optimization, CDN/WhiteNoise, S3-style uploads with Celery thumbnail pre-generation + on-the-fly fallback, full CI. Whether this is a new app or folded into an existing project is the user's decision at M6. Skipped permanently: sharding (demo adds nothing).

---

## STATE  *(update after every sitting)*

- **Last updated:** 2026-09-09
- **Where we are:** Lab 13 complete on branch `lab-13`, PR pending. **Arc B complete when it merges — M2 ticked in this branch.** GeneratedField tsvector + GinIndex; three-way comparison (icontains / naive FTS / indexed FTS) with hit and miss query shapes; naive-FTS-is-worst finding; stem-vs-substring semantics pinned in tests. README voice: plain register now standard (lab 12 entry = reference example).
- **Next action:** After merge: Arc C — Lab 14 response caching (cache rendered API responses, silk + locust before/after).
- **Session log:**
  - 2026-09-04 — plan created.
  - 2026-09-05 — scaffold: compose stack (healthchecks, .dockerignore), django project, settings package, postgres wired. Docker Desktop port-forward glitch fixed by recreate.
  - 2026-09-07 — models (user refactored to abstract TimestampedModel; kept uuid column, int PK), seed (500k comments), DRF+silk, tests+CI green (ruff excludes migrations), locustfile, README skeleton. **M0 done.**
  - 2026-09-08 — Lab 1 built + measured. Mid-lab detour: silk polluted test query counts because compose's DJANGO_SETTINGS_MODULE env var outranked pytest ini → root-cause fix (test.py settings, env var removed from compose/CI). Lesson recorded: one authoritative config voice per process, mind env-var scope. **Lab 1 done**, PR merged.
  - 2026-09-08 — Lab 2 built + measured (same sitting). Planner surprised us: predicted Seq Scan on wide count(*) but got Index Only Scan (visibility map) — corrected lesson: planner weighs heap pages touched, not rows matched. **Lab 2 done**, PR merged.
  - 2026-09-09 — Lab 3 built + measured. Leaked-rows incident (140k posts) traced to uncommitted-rollback assumption in lab-02's psql experiment; reseeded. Set-vs-dict typo in Response caught by test+ruff pointing at same line. **Lab 3 done**, PR merged.
  - 2026-09-09 — Lab 4 built + measured (same sitting). 37×/21× time/memory spread across full→only→values; user spotted values_list memory result before explanation. **Lab 4 done**, PR merged.
  - 2026-09-09 — Lab 5 built + load-tested (same sitting). Both 500s traced to stale worker, not code; locust runs by Claude at user's request. **Lab 5 done**, PR merged.
  - 2026-09-09 — Lab 6 built + measured (same sitting). 9→3 queries via cached_property; README emphasizes lifetime-based safety + mid-request write caveat. User set README voice rule: human technical prose, no conversational framing; review entries before PR. **Lab 6 done**, PR merged.
  - 2026-09-10 — Lab 7 built + measured. EXPLAIN contrast: generic hash-join-everything vs concrete nested-loop-the-page. **Lab 7 done**, PR merged, **M1 ticked**.
  - 2026-09-10 — Lab 8 built + measured (same sitting). Claude's predicted raw-SQL trap was wrong (cachalot patches the cursor); corrected to process-boundary trap, demonstrated via psql. Discussed industry context: transparent query caching is niche (MySQL 8.0 removed theirs); README verdict framed accordingly. **Lab 8 done**, PR merged. Chore PR (dev image stage + 3.13 re-pin + PYTHONUNBUFFERED fix) merged same day. Second branch mishap (lab-08 committed on lab-07) — Claude now creates/verifies lab branches itself.
  - 2026-09-10 — Lab 9 built + measured (same sitting). Cachalot cache-hit numbers nearly shipped as findings — caught, invalidated, re-measured cold. **Lab 9 done**, PR merged.
  - 2026-09-11 — Lab 10 built + measured. Live demo of denormalization's blast radius: new column name collided with lab 9's annotations. Full trade measured (read 15×, write +79%, rebuild 1.25 s). **Lab 10 done**, PR merged.
  - 2026-09-11 — Lab 11 built + verified (same sitting). Real streaming replication in compose; WAL propagation demoed live (0 rows → 1 row across the 2 s window); router split verified from the shell; anomaly deterministic. **Lab 11 done**, PR merged.
  - 2026-09-12 — Lab 12 built + measured. Locust client numbers proved useless under single-worker saturation (good "slower" than bad — noise); pivoted to silk medians + direct store-level thread bench. Discussed why counters flush to postgres instead of living in Redis. User challenged README voice ("does this look human-written?") — plain register adopted, memory updated. **Lab 12 done**, PR merged.
  - 2026-09-12 — Lab 13 built + measured (same sitting). Naive-FTS-slower-than-icontains surprise; miss-queries-scan-twice mechanism identified; migration cost reconstructed piecewise after another misread `time` output. **Lab 13 done → Arc B complete → M2.**
