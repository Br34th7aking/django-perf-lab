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
| — | — | — | — | — |