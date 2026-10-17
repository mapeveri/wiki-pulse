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
Wikimedia Pageviews API ┐
                        ├─► ingestion (Python producer) ─┐
Wikipedia HTML ─► crawler (Go producer) ────────────────┤
                                                         ▼
                                    Redpanda / Kafka (topics + <topic>.dlq)
                                                         │
                                            sink (Python consumer)
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

Every producer publishes events to a Kafka topic; the **sink** is the only
component that writes to ClickHouse. See [Ingestion pipeline](#ingestion-pipeline).

Everything runs on Kubernetes through Kustomize (see [`k8s/README.md`](k8s/README.md)),
and each service is containerized.

## Tech stack

| Layer | Technology |
| --- | --- |
| Ingestion | Python 3.10+, httpx, clickhouse-connect |
| Crawler | Go, goquery |
| Streaming | Redpanda (Kafka API), confluent-kafka, segmentio/kafka-go |
| Warehouse | ClickHouse |
| Transformations | dbt (dbt-clickhouse) |
| Serving | FastAPI, uvicorn |
| Frontend | React 18, TypeScript, Vite, Recharts |
| Platform | Docker, Kubernetes (Kustomize) |

## Repository layout

```
.
├── docker-compose.yml         # Local ClickHouse + Redpanda
├── kustomization.yaml         # Kustomize entrypoint (kubectl apply -k .)
├── Makefile                   # Developer entry points (make help)
├── .env.example               # Runtime configuration template
├── infra/clickhouse/init/     # Database + raw table schema (bootstrap)
├── ingestion/                 # Python producers + Kafka -> ClickHouse sink
├── crawler/                   # Go crawler (Wikipedia HTML -> Kafka producer)
├── dbt/                       # SQL transformations (staging + marts)
├── api/                       # FastAPI metrics service
├── dashboard/                 # React + TypeScript dashboard
└── k8s/                       # Kubernetes manifests (see k8s/README.md)
```

## Quickstart

Prerequisites: Docker, Python 3.10+, Go 1.23+, Node 20+.

```bash
# 1. Install everything (venv, python deps, dbt, go deps, node deps)
make setup

# 2. Start ClickHouse + Redpanda (databases, raw tables and topics are created)
make up

# 3. Run the sink: it consumes events and writes them to ClickHouse
make sink       # leaves running in the foreground

# 4. In another shell, publish data: audience from the API and content from the crawler
make ingest START=20260101 END=20260131
make crawl

# 5. Build the warehouse models
make transform

# 6. Serve the API and the dashboard
make api        # http://localhost:8000/docs
make dashboard  # http://localhost:5173
```

Run `make help` to see all targets. The dbt profile is created from
`dbt/profiles.example.yml` during `make setup`.

### Without the Makefile

Each component is a self-contained project with its own Dockerfile (under
`ingestion/`, `crawler/`, `api/`, `dbt/` and `dashboard/`); run them directly if
you prefer. The Kubernetes deployment is documented in [`k8s/README.md`](k8s/README.md).

## Configuration

Copy `.env.example` to `.env` and adjust as needed. It is loaded by both the
producers/sink and the API through `python-dotenv`.

| Variable | Default | Used by |
| --- | --- | --- |
| `CLICKHOUSE_HOST` | `localhost` | sink, API |
| `CLICKHOUSE_PORT` | `8123` | sink, API |
| `CLICKHOUSE_USER` | `default` | sink, API |
| `CLICKHOUSE_PASSWORD` | *(empty)* | sink, API |
| `CLICKHOUSE_DB` | `raw` | sink (write target) |
| `CLICKHOUSE_MARTS_DB` | `marts` | API (read target) |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | producers, sink |
| `KAFKA_CONSUMER_GROUP` | `wikipulse-sink` | sink |
| `WIKIMEDIA_USER_AGENT` | project placeholder | ingestion |
| `API_CORS_ORIGINS` | `*` | API |

The dashboard takes its API URL at build/dev time from `VITE_API_BASE_URL` (see
`dashboard/.env.example`), defaulting to `http://localhost:8000`.

## Ingestion pipeline

Producers never talk to ClickHouse. They publish one JSON event per record to a
Kafka topic, keyed by article so an article's events stay ordered:

| Producer | Topic | Trigger |
| --- | --- | --- |
| `wikipulse-ingest pageviews` | `pageviews.raw` | CLI / CronJob |
| `wikipulse-crawler` (Go) | `articles.raw` | CLI / CronJob |

The **sink** (`wikipulse-sink`) consumes those topics and is the only writer to
the `raw` layer. It provides:

- **batching** by size or time, and **at-least-once** delivery: offsets are
  committed only after a successful insert, so a crash reprocesses rather than
  loses a batch;
- **backpressure**: partitions are paused while a batch is being persisted;
- **dead-letter queue**: malformed records, and batches that fail to insert
  after retries, are sent to `<topic>.dlq` with the error and original payload.

Idempotency lives in the warehouse: the raw tables are `ReplacingMergeTree`, so
reprocessing a batch does not create duplicates.

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
| `GET /` | Service metadata |
| `GET /health` | Liveness probe |
| `GET /metrics/overview` | Totals for the dashboard header |
| `GET /metrics/articles` | Tracked articles with audience + content metrics |
| `GET /metrics/articles/{article}/timeseries` | Daily audience for one article |
| `GET /metrics/top-movers?direction=up\|down` | Largest week-over-week changes |
| `GET /metrics/trends` | Total daily audience across all articles |
| `GET /metrics/correlation` | Content size vs. audience points |
