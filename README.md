# MarketMind PyTrends

Microservice for collecting, normalizing and persisting Google Trends data via PyTrends.

## What it does

- Collects data from Google Trends via the PyTrends library
- Normalizes all responses into structured, typed records
- Persists raw responses and normalized data in PostgreSQL
- Exposes collected data via REST API
- Maintains full audit trail (every call creates a new ingestion run)
- Never overwrites historical data

## What it does NOT do

- Does NOT calculate MOS (Mean Opinion Score)
- Does NOT calculate Entropy Weight
- Does NOT calculate TOPSIS
- Does NOT use LLMs
- Does NOT know the Semantic Layer
- Does NOT know MarketMind business rules

## Architecture

Clean Architecture with the following layers:

```
app/
  api/routes/         # HTTP endpoints (no business logic)
  core/               # Configuration, logging, exceptions
  domain/             # Enums and domain entities
  clients/            # PyTrends API client with retry
  services/           # Orchestration (client + normalization + persistence)
  repositories/       # Data access layer
  db/models/          # SQLAlchemy models
  schemas/            # Pydantic request/response schemas
  utils/              # Normalization and time utilities
```

## Stack

- Python 3.12
- FastAPI + Pydantic v2
- PyTrends
- SQLAlchemy 2.x + asyncpg
- Alembic (migrations)
- PostgreSQL 16
- Docker + Docker Compose
- Poetry

## Running Locally

### Prerequisites

- Python 3.12+
- Poetry
- PostgreSQL 16 (or use Docker)

### Setup

```bash
# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Start PostgreSQL (if using Docker)
docker compose up postgres -d

# Run migrations
alembic upgrade head

# Start the API
uvicorn app.main:app --reload --port 8000
```

## Running with Docker

```bash
# Copy environment file
cp .env.example .env

# Build and start all services
docker compose up --build

# Run migrations (in another terminal)
docker compose exec marketmind-pytrends-api alembic upgrade head
```

The API will be available at `http://localhost:8000`.

## Swagger / OpenAPI

Once the API is running, access the interactive documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## pgAdmin

pgAdmin was consolidated into `marketmind-scoring` (single instance pointing at
all 5 services' databases). See `marketmind-scoring/README.md`.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `marketmind-pytrends` | Application name |
| `APP_ENV` | `local` | Environment |
| `APP_PORT` | `8000` | API port |
| `DATABASE_HOST` | `postgres` | PostgreSQL host |
| `DATABASE_PORT` | `5432` | PostgreSQL port |
| `DATABASE_NAME` | `marketmind_pytrends` | Database name |
| `DATABASE_USER` | `marketmind` | Database user |
| `DATABASE_PASSWORD` | `marketmind_password` | Database password |
| `DEFAULT_HL` | `en-US` | Default language |
| `DEFAULT_TZ` | `0` | Default timezone offset |
| `DEFAULT_TIMEFRAME` | `today 12-m` | Default timeframe |
| `DEFAULT_TIMEOUT` | `30` | Request timeout (seconds) |
| `DEFAULT_RETRIES` | `3` | Max retry attempts |
| `DEFAULT_BACKOFF` | `2` | Backoff multiplier |
| `LOG_LEVEL` | `INFO` | Logging level |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/interest-over-time` | Collect interest over time |
| `POST` | `/interest-by-region` | Collect interest by region |
| `POST` | `/related-queries` | Collect related queries |
| `POST` | `/related-topics` | Collect related topics |
| `POST` | `/suggestions` | Collect keyword suggestions |
| `GET` | `/requests/{id}` | Get stored trend request |
| `GET` | `/runs/{id}` | Get ingestion run details |

## Example curl

```bash
# Interest Over Time
curl -X POST http://localhost:8000/interest-over-time \
  -H "Content-Type: application/json" \
  -d '{"keyword": "air fryer", "country": "ES", "timeframe": "today 12-m", "language": "en-US"}'

# Suggestions
curl -X POST http://localhost:8000/suggestions \
  -H "Content-Type: application/json" \
  -d '{"keyword": "air fryer", "language": "en-US"}'

# Health Check
curl http://localhost:8000/health
```

## Running Tests

```bash
pytest
```

## Running Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Rollback last migration
alembic downgrade -1
```

## Linting and Type Checking

```bash
# Lint
ruff check .

# Format
black .

# Type check
mypy .
```
