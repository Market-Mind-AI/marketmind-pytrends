# MarketMind PyTrends

Collector of **Google Ads keyword data** for MarketMind, via
[DataForSEO](https://dataforseo.com): search volume, competition, CPC, monthly
searches and related keywords, per keyword and country, stored in PostgreSQL
with a full audit trail.

The name is historical. The service began on Google Trends through the PyTrends
library; that source was retired in migration `007` (2026-07-15), which dropped
every Trends table and created the Google Ads ones. The repository, the Compose
project and the database kept their names so that nothing already deployed had
to be renamed, and the `trend_requests` table stays as the per-request audit
record every collection still writes to.

## What it does

- Collects Google Ads search volume and keywords-for-keywords through the
  official `dataforseo-client` SDK.
- Normalises every response into typed rows and stores the raw response next
  to them. Every call opens a new ingestion run; nothing is ever overwritten.
- Serves what is stored, without collecting, so the scoring service can decide
  what still needs to be bought before spending.
- Reports what DataForSEO billed, on every response.

## What it does NOT do

- Does not compute the MOS, Rank Order Centroid or TOPSIS.
- Does not use LLMs and knows nothing of the catalogue or the method.

## Routes

| Method | Path | What it does |
|---|---|---|
| `GET` | `/healthz` | Is this process alive (no database). |
| `GET` | `/health` | Health check, including the database. |
| `POST` | `/search-volume` | Collect Google Ads search volume for 1..1000 keywords in one country. |
| `POST` | `/keywords-for-keywords` | Expand 1..20 seed keywords into related keywords in one country. |
| `GET` | `/requests/{id}` | One stored request (keyword, country, endpoint, run). |
| `GET` | `/runs/{id}` | One ingestion run (status, timing, error). |
| `POST` | `/stored/search-volume` | Read what is already stored for these keywords, and which are `missing` (optionally with `stale_after_days`). Nothing is fetched or billed. |
| `GET` | `/stored/related` | Read the related keywords stored for one `seed_keyword` in one `location`. Nothing is fetched or billed. |

Collection errors map to `503` when DataForSEO (or Google behind it) stayed down
through every attempt -- 429, timeouts and 5xx included, the same status every
MarketMind collector uses -- and `502` when it refused the request.

`missing` is read from the keyword checks (`keyword_checks`): one row per
(country, keyword) DataForSEO answered, kept current on every successful
collection. A keyword Google Ads has no volume for comes back without a row but
still counts as answered, so it is not billed again on every run -- the same
rule for a "no data" answer as in the indicator collectors.

```bash
curl -X POST http://localhost:8000/search-volume \
  -H "Content-Type: application/json" \
  -d '{"location": "ES", "language": "en-US", "keywords": ["air fryer", "robot vacuum"]}'
```

## Cost

Every task DataForSEO answers carries the amount it billed. The client logs
one line per task:

```
DATAFORSEO_COST endpoint=google_ads_search_volume_live cost_usd=0.075 status=20000 results=2
```

and a middleware adds the request's total to every response — error responses
included, since a failed task is billed too:

| Header | Meaning |
|---|---|
| `X-DataForSEO-Cost-USD` | Dollars billed for this request. |
| `X-DataForSEO-Calls` | Tasks sent. |
| `X-DataForSEO-Calls-Without-Cost` | Tasks whose answer carried no cost figure (so a zero total reads as "not reported", not "free"). |

The scoring service reads the headers and carries the figure into the
analysis's trace.

## How the client behaves

- **Sandbox by default in code** (`DATAFORSEO_USE_SANDBOX=true`): same auth and
  shapes, mock data, never billed. Every deployment sets it to `false`.
- **Retries** (`app/utils/retry.py`, the same in every collector):
  `DEFAULT_RETRIES` (5) attempts on 408, 429, 5xx, timeouts, network errors
  and transient `5xxxx` task codes, waiting `DEFAULT_BACKOFF` seconds doubled
  per attempt, with jitter, capped at 60 s; `Retry-After` is honoured up to the
  same cap. Other 4xx and `4xxxx` fail at once.
- **No client-side timeout**, unlike the other collectors' `DEFAULT_TIMEOUT`:
  a live call is billed whether or not this side gives up on it, and a
  keywords-for-keywords call has taken 120 s, so a cut-off would pay for the
  same call twice.
- **Timestamps**: timezone-aware UTC everywhere (`app/utils/time.py`).
- **The SDK is synchronous**, so the service runs each call in a worker thread
  (`asyncio.to_thread`). Without that a 120 s keywords-for-keywords call
  blocked the event loop, `/health` stopped answering and the liveness probe
  killed the container mid-collection.
- Country codes are ISO-2 and mapped to DataForSEO location names in
  `app/clients/dataforseo_locations.py`. Russia and Belarus are not in
  DataForSEO's catalogue; China is, but Google is blocked there, so it is
  refused rather than measured.

## Layout

```
app/
  api/routes/         # HTTP endpoints (no business logic)
  clients/            # DataForSEO client, retry loop, location table
  core/               # Settings, logging, exceptions, cost tally
  db/models/          # SQLAlchemy models
  domain/             # Enums
  repositories/       # Data access
  schemas/            # Pydantic request/response models
  services/           # Collection: client + normalisation + persistence
alembic/              # Migrations (007 is the Google Ads pivot)
scripts/              # verify_dataforseo_locations.py, run by hand
```

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `APP_NAME` | `marketmind-pytrends` | |
| `APP_ENV` | `local` | |
| `APP_PORT` | `8000` | Read by `docker-compose.yml` only; the app listens on 8000. |
| `DATABASE_HOST` / `PORT` / `NAME` / `USER` / `PASSWORD` | `localhost` / `5432` / `marketmind_pytrends` / `marketmind` / … | |
| `DATABASE_SSL_MODE` | `disable` | `require` at least on Azure. |
| `DEFAULT_HL` | `en-US` | Language when the request names none. |
| `DEFAULT_RETRIES` | `5` | Attempts per call, same in every collector. |
| `DEFAULT_BACKOFF` | `2` | First wait (seconds); doubles per attempt, with jitter, capped at 60 s. |
| `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` | `` | API password, not the account password. |
| `DATAFORSEO_USE_SANDBOX` | `true` | `false` in every deployment. |
| `LOG_LEVEL` | `INFO` | |

## Running

```bash
poetry install
cp .env.example .env
docker compose up -d postgres
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Or everything in Compose: `docker compose up --build`, then
`docker compose exec marketmind-pytrends-api alembic upgrade head`.
Swagger at `http://localhost:8000/docs`.

## Tests and lint

```bash
.venv/bin/python -m pytest -q -p no:cacheprovider
ruff check . && ruff format --check .
mypy .
```

## Team

Final project (TFM) for the *Máster en Ingeniería y Desarrollo de Soluciones de IA Generativa* — **EBIS Business Techschool**. The whole system and how to run it: [marketmind-ai](https://github.com/Market-Mind-AI/marketmind-ai).

- **Miguel Antonio Blanco Salcedo** — [@mikews93](https://github.com/mikews93)
- **Álvaro Augusto De Marco Neto** — [@ironeto](https://github.com/ironeto)
