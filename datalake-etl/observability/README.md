# Observability

## Recommended UI: Grafana + Prometheus

| UI | Purpose |
|----|---------|
| **Grafana** (`http://localhost:3000`) | ETL metrics — row counts, stage duration, success/fail |
| **Prefect UI** (`http://localhost:4200`) | Orchestration — run history, retries, task timeline |
| **Marquez** (optional, via OpenLineage) | Column/table lineage graph |

Grafana is the best fit for **operational ETL metrics** (rowcount, latency, SLAs). Prefect covers **workflow state**; keep them separate.

## Metrics emitted

| Metric | Labels | Meaning |
|--------|--------|---------|
| `etl_stage_duration_seconds` | `stage`, `layer` | Histogram of per-stage wall time |
| `etl_stage_rows` | `stage`, `layer`, `entity` | Rows after stage (from lake Parquet) |
| `etl_stage_last_success` | `stage`, `layer` | 1 = last run OK |
| `etl_pipeline_duration_seconds` | `pipeline` | Full flow duration |
| `etl_pipeline_last_success` | `pipeline` | 1 = last pipeline OK |

## Local stack

```bash
# Terminal 1 — observability + Prefect server
docker compose -f compose.observability.yml up -d pushgateway prometheus grafana prefect-server

# Terminal 2 — run pipeline via Prefect flow (pushes metrics)
cd datalake-etl
export PROMETHEUS_PUSHGATEWAY_URL=http://localhost:9091
make prefect

# Grafana: http://localhost:3000  (admin / admin)
# Dashboard: ETL → Medallion ETL
```

## Without Docker

```bash
export PROMETHEUS_PUSHGATEWAY_URL=http://localhost:9091  # optional
make all   # records metrics; pushes if gateway URL set
```

Disable metrics: `METRICS_DISABLED=true`

## Prod pattern

1. **Prefect** — `prefect deploy` / worker on ECS with `PREFECT_API_URL` pointing at Prefect Cloud or self-hosted server.
2. **Prometheus** — scrape Pushgateway (batch jobs) or `METRICS_PORT` sidecar on long-running workers.
3. **Grafana** — managed or self-hosted; alert on `etl_pipeline_last_success == 0` or row-count deltas.
