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

## External tool APIs

```bash
WEATHERAPI_API_KEY=your-weatherapi-key
EXCHANGERATE_API_KEY=your-exchangerate-api-key
```

- Weather: [WeatherAPI.com](https://www.weatherapi.com/docs/) current weather (`/v1/current.json`)
- Currency: [ExchangeRate-API](https://www.exchangerate-api.com/docs/pair-conversion-requests) pair rate (`/v6/{key}/pair/{from}/{to}`); amount conversion is computed in-app

## Redis: caching and rate limiting

Redis is configured via `REDIS_URL` and powers two features:

1. **Tool response caching** — weather, currency, and summary results are stored in Redis to avoid repeat external/LLM calls.
2. **Rate limiting** — DRF `ScopedRateThrottle` on `POST /api/query` stores per-client request counters in Django cache. Because cache uses Redis, those counters survive process restarts and work across workers.

`POST /api/query` is rate limited because each request can trigger LLM, weather, or currency API calls. Limiting traffic protects cost, upstream quotas, and service stability.

**Current limit:** 10 requests per minute per client IP on `POST /api/query`.

When exceeded, the API returns HTTP `429` with:

```json
{
  "success": false,
  "message": "Rate limit exceeded. Please try again later.",
  "data": null
}
```

**Future improvement:** a token-bucket or sliding-window Redis rate limiter for finer-grained control.

### Manual rate-limit test

Send more than 10 requests to `POST /api/query` within one minute (same client/IP). The 11th request should return `429 Too Many Requests`.

```bash
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST http://127.0.0.1:8000/api/query/ \
    -H "Content-Type: application/json" \
    -d '{"query": "What is the weather in London?"}'
done
```
