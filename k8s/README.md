# Kubernetes deployment

Manifests to run WikiPulse on a Kubernetes cluster. Everything is wired through
[Kustomize](https://kustomize.io/), so you can apply or customize it without
editing YAML by hand.

## What gets deployed

| Resource | Purpose |
| --- | --- |
| `clickhouse` StatefulSet + Service | Analytical warehouse (persistent volume) |
| `clickhouse-init` ConfigMap | Databases and raw schema, applied on first boot |
| `api` Deployment + Service | Metrics API (2 replicas, HPA up to 6) |
| `api` HPA | Horizontal autoscaling on CPU (70%) |
| `dashboard` Deployment + Service | Nginx serving the built SPA |
| `ingestion-pageviews` CronJob | Daily audience ingestion (03:00) |
| `crawler-articles` CronJob | Weekly content crawl (Mondays 04:00) |
| `topics` ConfigMap | Shared list of tracked articles |

## Build and push images

Build from the repository root (see the Dockerfiles):

```bash
docker build -f api/Dockerfile       -t <registry>/wikipulse-api:latest .
docker build -f ingestion/Dockerfile -t <registry>/wikipulse-ingestion:latest .
docker build -f crawler/Dockerfile   -t <registry>/wikipulse-crawler:latest .
docker build -f dashboard/Dockerfile --build-arg VITE_API_BASE_URL=/api \
  -t <registry>/wikipulse-dashboard:latest .
docker push <registry>/wikipulse-api:latest   # ...and the rest
```

Point the manifests at your registry. The Kustomization lives at the repository
root (so it can reuse the ClickHouse init SQL and the topics file):

```bash
kustomize edit set image wikipulse/api=<registry>/wikipulse-api:latest
kustomize edit set image wikipulse/ingestion=<registry>/wikipulse-ingestion:latest
kustomize edit set image wikipulse/crawler=<registry>/wikipulse-crawler:latest
kustomize edit set image wikipulse/dashboard=<registry>/wikipulse-dashboard:latest
```

## Deploy

From the repository root:

```bash
kubectl apply -k .
kubectl -n wikipulse get pods -w
```

## Run the transformations

dbt is run out of band (CI job, operator, or a one-off pod) against the
`clickhouse` Service. Run it the same way as locally, pointing the profile at
`clickhouse:8123`.

## Observability

- The API and dashboard expose `/health` and `/healthz` and are wired with
  readiness/liveness probes.
- The ClickHouse StatefulSet carries `prometheus.io/scrape` annotations and
  exposes native metrics on port `9363`, so a Prometheus setup with
  Kubernetes service discovery will pick it up.
- `raw.ingestion_runs` records every ingestion run (status, rows, error) for
  pipeline-level monitoring directly from SQL.

## Notes

- The dashboard embeds `VITE_API_BASE_URL` at build time. Serving it behind the
  same host as the API (e.g. `/api`) avoids CORS entirely.
- ClickHouse runs as a single replica here; scale to a cluster (ClickHouse
  Operator, Remote_servers, etc.) only if you need it — out of scope for this
  project.
