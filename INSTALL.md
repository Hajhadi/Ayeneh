# Ayeneh Installation Guide

## Prerequisites

- Python 3.13+
- PostgreSQL 16+ with pgvector extension
- Redis 7+ (optional, for caching)
- Node.js 22+ and pnpm (for frontend)

## Quick Start

### 1. Clone and install backend

```bash
cd apps/backend
pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start the database

```bash
docker-compose up -d postgres redis
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the API

```bash
uvicorn ayeneh.main:app --host 0.0.0.0 --port 8000
```

### 6. Start the frontend

```bash
cd frontend
pnpm install
pnpm dev
```

### 7. Open the wizard

Navigate to http://localhost:3000/wizard to complete setup.

## Docker Compose (Full Stack)

```bash
docker-compose up
```

This starts: API, Worker, PostgreSQL+pgvector, Redis, Prometheus, Grafana.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AYENEH_DATABASE_URL` | postgresql+asyncpg://... | PostgreSQL connection |
| `AYENEH_REDIS_URL` | redis://localhost:6379/0 | Redis connection |
| `AYENEH_LLM_PROVIDER` | litellm | Default LLM provider |
| `AYENEH_LLM_OPENAI_API_KEY` | | OpenAI API key |
| `AYENEH_LLM_ANTHROPIC_API_KEY` | | Anthropic API key |
| `AYENEH_LLM_GEMINI_API_KEY` | | Gemini API key |
| `AYENEH_LLM_DEFAULT_MODEL` | gpt-4o-mini | Default model |
| `AYENEH_DEBUG` | false | Debug mode |
