# Nishchit Backend

FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL backend.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL or Docker

Copy `.env.example` to `.env` and replace its placeholder values before running.

## Setup

```bash
cd backend
cp .env.example .env
uv sync
```

Set `CORS_ALLOWED_ORIGINS` to a comma-separated list of allowed frontend origins.

## Run locally

```bash
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

API available at `http://localhost:8000`, health check at
`http://localhost:8000/api/v1/health`.

## Run with Docker

```bash
cd backend
cp .env.example .env
docker compose up --build
```

The API container waits for PostgreSQL, applies migrations, and then starts the server.

## Database migrations

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

## Tests

```bash
uv run pytest
```

## Lint and type check

```bash
uv run ruff check .
uv run mypy app
```
