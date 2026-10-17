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
                                           ├─ staging  (cleaned, deduped)
                                           └─ marts    (aggregates for BI)
                                                │
                                         API (FastAPI)
                                                │
                                        Dashboard (React + TS)
```

## Repository layout

```
.
├── docker-compose.yml         # Local ClickHouse
├── infra/clickhouse/init/     # Database + raw table schema (bootstrap)
├── ingestion/                 # Python ingestion jobs (Wikimedia API -> ClickHouse)
├── crawler/                   # Go crawler (Wikipedia HTML -> ClickHouse)
├── dbt/                       # SQL transformations (staging + marts)
├── api/                       # FastAPI metrics service
├── dashboard/                 # React + TypeScript dashboard
└── k8s/                       # Kubernetes manifests
```

## Quickstart

1. Copy the environment file and adjust it if needed:

   ```bash
   cp .env.example .env
   ```

2. Start ClickHouse:

   ```bash
   docker compose up -d clickhouse
   ```

3. The databases (`raw`, `staging`, `marts`) and the raw tables are created
   automatically on first boot from `infra/clickhouse/init/`.

## Status

Work in progress. See the roadmap below.

- [x] Project skeleton and local ClickHouse
- [x] Raw schema bootstrap
- [ ] Python ingestion (Wikimedia Pageviews)
- [ ] Go crawler (Wikipedia HTML)
- [ ] dbt models (staging + marts)
- [ ] FastAPI metrics API
- [ ] React dashboard
- [ ] Kubernetes deployment
