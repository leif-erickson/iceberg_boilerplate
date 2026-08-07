# lakehouse

Governance-driven medallion lakehouse: a version-controlled metadata registry
drives cleansing, validation, quality gates, and Iceberg publishing.

**Stack:** Python 3.12 · Polars · Pandera · Apache Iceberg (PyIceberg) · Dagster
· OpenLineage · Prometheus/Grafana · Soda (Great Expectations compatible) ·
Terraform (AWS Glue + Lake Formation + S3).

## Architecture

```
governance/ (Collibra-lite registry: contracts, cleansing rules, canonical maps, quality gates)
        │  drives ▼
raw CSV ──▶ bronze ──▶ silver ─────────────▶ gold (Apache Iceberg)
 (Polars)   (land)    │ Polars cleansing:      │ PyIceberg write
                      │  • UTC / ISO-8601      │  local: SQLite catalog + FS
                      │  • scrub diacritics    │  prod:  AWS Glue + S3
                      │  • US number format    │
                      │ canonical dept mapping │
                      │ Pandera schema check   │
                      │ quality gates ─────────┼─▶ native + SodaCL (+ GX)
                      ▼                        ▼
        OpenLineage events           Prometheus metrics ──▶ Grafana
```

Orchestrated by **Dagster** (`dagster_project/`): `bronze_orders` →
`silver_orders` (+ `orders_quality_gates` asset check) → `orders_iceberg`.

## Quick start

```bash
cd lakehouse
make setup                 # venv + deps
make run                   # bronze -> silver -> Iceberg (prints per-gate results)
make test                  # pytest
make dagster-dev           # Dagster UI at http://localhost:3000
make sodacl                # regenerate governance/soda/orders.yml from the contract
```

## Data quality with Soda / Great Expectations

Gates live in the contract and run natively (Dagster asset check) and via Soda:

```bash
# build a DuckDB table from the cleansed output, then scan with the generated checks
soda scan -d lakehouse -c governance/soda/configuration.duckdb.yml governance/soda/orders.yml
```

Great Expectations is a supported alternative — see `governance/README.md`.

## Observability

```bash
docker compose -f observability/compose.observability.yml up -d
export PROMETHEUS_PUSHGATEWAY_URL=http://localhost:9091
make run                   # metrics pushed to the gateway
# Grafana http://localhost:3001 (admin/admin) -> "Lakehouse — Medallion & Data Quality"
```

Metrics: `lakehouse_stage_rows`, `lakehouse_stage_duration_seconds`,
`lakehouse_stage_last_success`, `lakehouse_quality_checks_total`,
`lakehouse_quality_gate_pass`.

## Environment variables (local → prod parity)

| Variable | Local default | Prod |
| --- | --- | --- |
| `LAKE_ROOT` | `./lake` | `s3://<bucket>` |
| `ICEBERG_CATALOG_URI` | `sqlite:///lake/catalog.db` | Glue catalog |
| `ICEBERG_WAREHOUSE` | `lake/warehouse` | `s3://<bucket>` |
| `DS` | `2026-06-05` | orchestrator partition |
| `OPENLINEAGE_CONFIG` | `lakehouse/openlineage.yml` | HTTP transport (Marquez) |
| `PROMETHEUS_PUSHGATEWAY_URL` | unset | Pushgateway URL |

## Cloud infra (AWS-native)

`infra/terraform/` provisions the S3 warehouse, Glue Data Catalog databases
(Iceberg namespaces per layer), Lake Formation governance, and the pipeline IAM
role:

```bash
cd infra/terraform
terraform init && terraform apply -var-file=terraform.tfvars
```
