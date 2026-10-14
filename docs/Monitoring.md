# Monitoring

The Docker Compose stack includes a full metrics pipeline for the API, the machine, and the database.

```text
fastapi (/metrics) ──┐
node-exporter ───────┤
postgres-exporter ───┼──>  Prometheus  ──>  Grafana
qdrant (/metrics) ───┤
prometheus (self) ───┘
```

| Service | URL on the host | Purpose |
|---|---|---|
| Prometheus | http://localhost:9090 | Collects and stores metrics, runs queries |
| Grafana | http://localhost:3000 | Dashboards on top of Prometheus |
| API metrics | http://localhost:8000/metrics | Raw Prometheus-format metrics from the API |

In production, do not publish these ports. See [Deployment](deployment.md#monitoring-access).

## What Prometheus scrapes

Defined in `docker/prometheus/prometheus.yml`. The scrape and evaluation interval is 15 seconds.

| Job | Target | Path | What you get |
|---|---|---|---|
| `fastapi` | `fastapi:8000` | `/metrics` | HTTP request metrics from the API |
| `node-exporter` | `node-exporter:9100` | `/metrics` | Host CPU, memory, disk, network |
| `postgres` | `postgres-exporter:9187` | `/metrics` | PostgreSQL connections, transactions, table and database stats |
| `qdrant` | `qdrant:6333` | `/metrics` | Metrics of the Qdrant service |
| `prometheus` | `localhost:9090` | `/metrics` | Prometheus' own health (the job name keeps its current spelling) |

Targets use Docker service names, so they resolve only inside the Compose network. Check their state at http://localhost:9090/targets.

## API metrics

A middleware in `src/utils/metrics.py` records every request and exposes the result at `GET /metrics`.

| Metric | Type | Labels | Description |
|---|---|---|---|
| `http_requests_total` | counter | `method`, `endpoint`, `status` | Total requests handled |
| `http_request_duration_seconds` | histogram | `method`, `endpoint` | Request latency in seconds |

`endpoint` is the API route, so project IDs do not become separate series. The histogram uses the client library's default buckets, which suit fast endpoints. Answering a question can take several seconds because it waits on the LLM, so you may want custom buckets later.

Beyond these two, the endpoint also exposes the default process and Python runtime metrics from the Prometheus client library.

### Multiple workers

The Docker image runs several `uvicorn` workers, and each worker keeps its own counters. A scrape of `/metrics` reaches one worker at random, so counters can appear to jump or reset between scrapes. For accurate numbers, either run a single worker, or switch the Prometheus client to multiprocess mode (set `PROMETHEUS_MULTIPROC_DIR` and serve the aggregated registry). This is a known limitation.

## Setting up Grafana

Grafana starts empty, with no data source and no dashboards.

### 1. Log in

Open http://localhost:3000 and sign in with the admin user and password from `docker/envv/.env.grafana`.

### 2. Add the data source

Go to **Connections**, then **Data sources**, then **Add data source**, and choose **Prometheus**. Set the URL to:

```text
http://prometheus:9090
```

Use the service name, not `localhost`, because Grafana reaches Prometheus over the Compose network. Save and test.

### 3. Import dashboards

Use **Dashboards**, then **New**, then **Import**, and enter a dashboard ID from grafana.com:

| Dashboard | ID | Source |
|---|---|---|
| Node Exporter Full | `1860` | Host metrics from `node-exporter` |
| PostgreSQL Database | `9628` | Database metrics from `postgres-exporter` |

Select your Prometheus data source when asked. Dashboard IDs are community-maintained, so confirm they still exist on grafana.com.

For the API itself, build a dashboard from the queries below.

## Useful queries

Run these in the Prometheus UI (**Graph** tab) or in Grafana panels.

**Request rate per endpoint**

```promql
sum by (endpoint) (rate(http_requests_total[5m]))
```

**Error rate (5xx)**

```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
```

**Share of failed requests**

```promql
sum(rate(http_requests_total{status=~"[45].."}[5m]))
  / sum(rate(http_requests_total[5m]))
```

**95th percentile latency per endpoint**

```promql
histogram_quantile(
  0.95,
  sum by (le, endpoint) (rate(http_request_duration_seconds_bucket[5m]))
)
```

**Average latency of answers**

```promql
rate(http_request_duration_seconds_sum{endpoint=~".*answer.*"}[5m])
  / rate(http_request_duration_seconds_count{endpoint=~".*answer.*"}[5m])
```

**Is every target up?**

```promql
up
```

Bear in mind that `400` responses include normal client-side outcomes such as a search before indexing, so alert on `5xx` and on latency first.

## Ideas for alerts

Prometheus is configured without alert rules or an Alertmanager. Good first alerts once you add them:

- Any target with `up == 0` for 2 minutes
- API 5xx rate above zero for 5 minutes
- p95 latency of the answer endpoint above your acceptable limit
- Host disk usage above 85 percent (uploads and the database grow over time)
- Postgres connections close to the configured maximum

## Troubleshooting

See [Troubleshooting](troubleshooting.md#monitoring) for targets that are down, empty Grafana panels, and login problems.
