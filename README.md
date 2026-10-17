# WikiPulse

An audience & content analytics platform. It tracks how a curated set of topics
performs over time and relates **content structure** with **audience traffic**,
then exposes the KPIs through an API and a web dashboard.

## Product

WikiPulse answers questions such as:

- Which articles gained or lost the most audience week over week?
- How is the traffic of a topic trending over time?
- Is there a relationship between content attributes (length, links, sections)
  and the audience an article attracts?

The product is a dashboard backed by a REST API. Every screen is powered by the
same metrics endpoints, so the API can also be consumed by external clients.

## Data sources

| Source | What it provides | How |
| --- | --- | --- |
| Wikimedia Pageviews API | Daily audience per article | Public REST API (no key) |
| Wikipedia (HTML) | Content structure per article | Go crawler |

The value of the platform comes from joining both: the API provides *traffic*,
the crawler provides *content structure*, and the warehouse models them together.

## Architecture

```
Wikimedia Pageviews API ─┐
                         ├─► ingestion (Python) ─┐
Wikipedia HTML ─► crawler (Go) ─────────────────┤
                                                ▼
                                           ClickHouse
                                           ├─ raw      (as ingested)
                                           ├─ staging  (cleaned, deduped, dbt)
                                           └─ marts    (aggregates, dbt)
                                                │
                                         API (FastAPI)
                                                │
                                        Dashboard (React + TS)
```

Everything runs on Kubernetes through Kustomize (see [`k8s/README.md`](k8s/README.md)),
and each service is containerized.

## Tech stack

| Layer | Technology |
| --- | --- |
| Ingestion | Python 3.10+, httpx, clickhouse-connect |
| Crawler | Go, goquery |
| Warehouse | ClickHouse |
| Transformations | dbt (dbt-clickhouse) |
| Serving | FastAPI, uvicorn |
| Frontend | React 18, TypeScript, Vite, Recharts |
| Platform | Docker, Kubernetes (Kustomize) |

## Repository layout

```
.
├── docker-compose.yml         # Local ClickHouse
├── kustomization.yaml         # Kustomize entrypoint (kubectl apply -k .)
├── infra/clickhouse/init/     # Database + raw table schema (bootstrap)
├── ingestion/                 # Python ingestion jobs (Wikimedia API -> ClickHouse)
├── crawler/                   # Go crawler (Wikipedia HTML -> ClickHouse)
├── dbt/                       # SQL transformations (staging + marts)
├── api/                       # FastAPI metrics service
├── dashboard/                 # React + TypeScript dashboard
└── k8s/                       # Kubernetes manifests
```

## Quickstart

Prerequisites: Docker, Python 3.10+, Go 1.23+, Node 20+.

```bash
# 1. Install everything (venv, python deps, dbt, go deps, node deps)
make setup

# 2. Start ClickHouse (databases and raw tables are created on first boot)
make up

# 3. Load data: audience from the API and content from the crawler
make ingest START=20260101 END=20260131
make crawl

# 4. Build the warehouse models
make transform

# 5. Serve the API and the dashboard
make api        # http://localhost:8000/docs
make dashboard  # http://localhost:5173
```

Run `make help` to see all targets. The dbt profile is created from
`dbt/profiles.example.yml` during `make setup`.

### Without the Makefile

Each component is a self-contained project; see the README/Dockerfile inside
`ingestion/`, `crawler/`, `api/` and `dashboard/`.

## Data model

The warehouse follows a `raw -> staging -> marts` layering:

- **raw** stores data exactly as ingested. The audience and article tables are
  `ReplacingMergeTree`, so re-running an ingestion is idempotent.
- **staging** (`dbt`) deduplicates and types the raw data.
- **marts** (`dbt`) contains the analytical models used by the API:
  `dim_articles`, `fct_article_daily_traffic` and `mart_article_traffic`
  (per-article totals and week-over-week change).

## API

Interactive docs at `/docs`. Main endpoints:

| Endpoint | Description |
| --- | --- |
| `GET /metrics/overview` | Totals for the dashboard header |
| `GET /metrics/articles` | Tracked articles with audience + content metrics |
| `GET /metrics/articles/{article}/timeseries` | Daily audience for one article |
| `GET /metrics/top-movers?direction=up\|down` | Largest week-over-week changes |
| `GET /metrics/trends` | Total daily audience across all articles |
| `GET /metrics/correlation` | Content size vs. audience points |
