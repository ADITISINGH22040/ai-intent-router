# AI Intent Router

Django REST Framework project skeleton with PostgreSQL and Redis.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d
python manage.py migrate
python manage.py runserver
```

- Admin: http://127.0.0.1:8000/admin/
- API: http://127.0.0.1:8000/api/

Postgres is exposed on host port **5433** (avoids conflict with a local Postgres on 5432).
