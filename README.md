# AI Intent Router

Django REST Framework project with PostgreSQL, Redis, and `django-environ`.

## Layout

```
ai-intent-router/
├── manage.py
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── ai_intent_router/     # project settings
└── apps/
    └── router/           # main app
        ├── constants/
        ├── services/
        ├── llm/
        ├── tools/
        └── tests/
```

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

## LLM providers

Set `LLM_PROVIDER` to `ollama` (default) or `gemini`.

**Ollama (local):** run `ollama serve`, pull the model (`ollama pull gemma3:4b`), then:

```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=gemma3:4b
```

**Gemini:** set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY`.
