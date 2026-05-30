# AI Intent Router

Django REST Framework service that classifies user queries by intent and routes them to the appropriate tools.

## Stack

- Django 6 + Django REST Framework
- PostgreSQL (via `psycopg`)
- Redis (via `django-redis` + `redis`)
- Environment config with `python-dotenv`

## Project layout

```
ai-intent-router/
├── manage.py
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── config/              # Django project (settings, urls)
└── router/              # Main app
    ├── constants/
    ├── services/
    ├── llm/
    ├── tools/
    └── tests/
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment variables and start infrastructure:

   ```bash
   cp .env.example .env
   docker compose up -d
   ```

4. Run migrations and start the dev server:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

Admin: http://127.0.0.1:8000/admin/  
API base: http://127.0.0.1:8000/api/

## Development

- `python manage.py check` — validate project configuration
- `python manage.py test router` — run app tests
