# datalake-etl

DuckDB-centric medallion ETL scaffold: **local filesystem lake → same SQL → S3 lake in prod**.

| Layer  | Tool              | Lake path                          |
|--------|-------------------|------------------------------------|
| Bronze | DuckDB SQL        | `bronze/{source}/dt=YYYY-MM-DD/`   |
| Silver | dbt-duckdb        | `silver/{entity}/dt=YYYY-MM-DD/`   |
| Gold   | dbt-duckdb        | `gold/{mart}/dt=YYYY-MM-DD/`       |

## Quick start (local)

```bash
cd datalake-etl
make setup
make all
```

Or step by step:

```bash
export LAKE_ROOT=./lake DS=2026-06-05
make fixtures    # sample staging data
make ingest      # thin Python → staging/
make bronze      # DuckDB SQL → bronze/
make silver      # dbt silver.*
make gold        # dbt gold.*
make test        # pytest + dbt test
```

## Docker

```bash
make docker-all DS=2026-06-05
# shell inside container:
docker compose run --rm etl-shell
```

## Layout

```
datalake-etl/
├── ingest/           # thin Python IO only
├── sql/bronze/       # landing SQL (DuckDB COPY)
├── dbt/              # silver + gold models, tests, macros
├── scripts/          # runners (bronze SQL, full pipeline)
├── tests/            # pytest on fixtures + integration
├── infra/            # AWS deployment notes
└── lake/             # local data (gitignored)
```

## Environment variables

| Variable         | Local default        | Prod example                    |
|------------------|----------------------|---------------------------------|
| `LAKE_ROOT`      | `./lake`             | `s3://company-datalake`         |
| `DS`             | `2026-06-05`         | partition date from orchestrator |
| `DBT_TARGET`     | `local`              | `prod`                          |
| `DBT_DUCKDB_PATH`| `duckdb/local.duckdb`| `/tmp/prod.duckdb`              |

## Adding a new entity

1. Add `ingest/{entity}_api.py` (if needed) → `staging/{entity}/`
2. Add `sql/bronze/{entity}_land.sql`
3. Add `dbt/models/silver/{entity}.sql` + `schema.yml`
4. Add gold marts that `ref()` silver models
5. Extend `make all` / `run_pipeline.py` if you add new bronze SQL files (auto-discovered)

## Prod

See [infra/README.md](infra/README.md) for ECS + Glue external table sketch. The container entrypoint is:

```bash
python scripts/run_pipeline.py all
```
