# datalake-etl

DuckDB-centric medallion ETL: **local filesystem lake → same SQL → S3 lake in prod**.

| Layer | Tool | Lake path |
|-------|------|-----------|
| Bronze | DuckDB SQL | `bronze/{source}/dt=YYYY-MM-DD/` |
| Silver | dbt-duckdb | `silver/{entity}/dt=YYYY-MM-DD/` |
| Gold dimensional | dbt-duckdb | `gold/dimensional/{dim\|fct}/dt=.../` |
| Gold denormalized | dbt-duckdb | `gold/denormalized/{mart}/dt=.../` |

## Quick start

```bash
cd datalake-etl
make setup
make all
```

Pipeline order: **fixtures → ingest → bronze → GX → silver → GX → gold (dim + denorm) → pytest + dbt test**

## Orchestration (Prefect) + metrics (Prometheus / Grafana)

| Tool | UI | Use for |
|------|-----|---------|
| **Prefect** | http://localhost:4200 | Run history, retries, task timeline |
| **Grafana** | http://localhost:3000 | Row counts, stage duration, success/fail |
| Prometheus | http://localhost:9090 | Metrics store (scrape Pushgateway) |

```bash
make observability-up          # Prometheus + Grafana + Pushgateway + Prefect server
make prefect                   # run flow; metrics -> Pushgateway
# Grafana: admin / admin → dashboard "Medallion ETL"
```

See [observability/README.md](observability/README.md) for metric names and prod patterns.

## Gold mart styles

### Dimensional (Kimball)

```
silver/orders ──▶ gold/dimensional/dim_customer.sql
              └──▶ gold/dimensional/fct_orders.sql  (refs dim)
```

### Denormalized (wide / summary)

```
silver/orders + silver/customers
  ├──▶ gold/denormalized/mart_orders_wide.sql
  └──▶ gold/denormalized/mart_revenue_daily.sql
```

```bash
make gold-dimensional    # dim + fact only
make gold-denormalized   # wide + summary marts
make gold                # both
```

## Data quality

| Tool | Role | When |
|------|------|------|
| **Great Expectations** | Lake partition checks (volume, ranges, enums) | After bronze & silver |
| **dbt test** | Model contracts (`unique`, `not_null`, `relationships`) | After gold |

```bash
make gx-bronze
make gx-silver
```

**Soda:** intentionally not included — GX + dbt tests cover the same ground. See [quality/README.md](quality/README.md).

## OpenLineage

| Step | Emitter |
|------|---------|
| Bronze SQL | `scripts/lineage.py` |
| GX checkpoints | `scripts/lineage.py` |
| Silver / gold dbt | `dbt-ol` (auto when `OPENLINEAGE_CONFIG` is set) |

Local events append to `lineage/events.ndjson`:

```bash
make bronze
make lineage    # tail recent events
```

Prod: set `OPENLINEAGE_URL` (Marquez) — see [quality/openlineage/](quality/openlineage/).

Disable lineage: `OPENLINEAGE_DISABLED=true`

## Layout

```
datalake-etl/
├── ingest/                 # thin Python IO
├── sql/bronze/             # DuckDB landing SQL
├── dbt/models/
│   ├── silver/
│   └── gold/
│       ├── dimensional/    # dim_*, fct_*
│       └── denormalized/   # mart_* wide tables
├── quality/
│   ├── suites/             # Great Expectations
│   └── openlineage/        # OL transport config
├── scripts/                # pipeline, GX, lineage
└── lineage/                # local OL events (gitignored)
```

## Environment variables

| Variable | Local | Prod |
|----------|-------|------|
| `LAKE_ROOT` | `./lake` | `s3://company-datalake` |
| `DS` | `2026-06-05` | orchestrator partition |
| `OPENLINEAGE_CONFIG` | `quality/openlineage/openlineage.local.yml` | HTTP/Marquez config |
| `OPENLINEAGE_NAMESPACE` | `datalake-etl` | `prod.datalake-etl` |

## Prod

```bash
python scripts/run_pipeline.py all
```

See [infra/README.md](infra/README.md) for ECS + Glue external tables.
