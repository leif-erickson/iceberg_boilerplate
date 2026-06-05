# Data quality and lineage

## Great Expectations (primary)

GX checkpoints run after bronze and silver land on the lake:

```bash
make gx-bronze
make gx-silver
make gx-all
```

Suites live in `quality/suites/` as Python modules (easy to extend and test locally).

## Soda — not included (recommendation)

**Skip Soda** for this stack. You already have:

| Layer | Tool |
|-------|------|
| Model contracts | `dbt test` (`unique`, `not_null`, …) |
| Lake partitions | Great Expectations (`quality/suites/`) |

Adding Soda would duplicate GX + dbt without new capability. Consider Soda only if a downstream team mandates Soda Cloud scans.

## OpenLineage

| Step | Emitter |
|------|---------|
| Bronze SQL | `scripts/lineage.py` context manager |
| GX checkpoints | `scripts/lineage.py` |
| Silver / gold dbt | `dbt-ol` when lineage is enabled |

### Local (file transport)

```bash
export OPENLINEAGE_CONFIG=quality/openlineage/openlineage.local.yml
export OPENLINEAGE_NAMESPACE=datalake-etl
make all
cat lineage/events.ndjson
```

### Prod (Marquez / HTTP)

```bash
export OPENLINEAGE_URL=http://marquez:5000
export OPENLINEAGE_NAMESPACE=prod.datalake-etl
```

Lineage events append to `./lineage/events.ndjson` locally. Point Marquez at the HTTP transport in prod (`quality/openlineage/openlineage.prod.yml`).
