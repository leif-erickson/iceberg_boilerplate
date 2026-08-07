# Governance registry (the "Collibra-lite" layer)

This directory is a **version-controlled metadata store**: the single source of
truth for dataset schemas, cleansing rules, canonical reference data, and data
quality gates. Everything downstream — Polars cleansing, Pandera validation,
Soda/GX checks, and the Iceberg table schema — is generated from these files, so
governance lives with the code and moves through pull requests and CI.

## Why not just buy Collibra?

Collibra is a business-facing governance suite (glossary, ownership, policies,
stewardship workflows). For a code-first lakehouse you usually want two layers,
and both have strong AWS-native / open-source options:

| Need | Collibra feature | Recommended here |
| --- | --- | --- |
| Technical catalog (tables, schemas, partitions) | Catalog | **AWS Glue Data Catalog** (Iceberg catalog; see `../infra/terraform`) |
| Fine-grained access governance | Policies | **AWS Lake Formation** (row/column/tag permissions) |
| Business glossary, ownership, stewardship, tags | Glossary/Workflows | **DataHub** or **OpenMetadata** (OSS Collibra alternatives) |
| Column/table lineage graph | Lineage | **Marquez** (OpenLineage), or lineage in DataHub/OpenMetadata |
| Machine-readable data contracts | — | **Open Data Contract Standard (ODCS)** / `datacontract-cli` |
| Cleansing rules + canonical values + gates | Reference data / rules | **this registry** (`contracts/`, `canonical/`, `cleansing_rules.yaml`) |

Recommended pattern: keep this registry as the authored source of truth in git,
provision the technical catalog with Glue + Lake Formation (Terraform), and
**push** the registry to DataHub/OpenMetadata (glossary terms, ownership, tags)
and Marquez (lineage via the OpenLineage events this pipeline already emits).
The registry format is intentionally close to ODCS so it can be exported.

## Layout

```
governance/
├── cleansing_rules.yaml     # documented rule library (types + default params)
├── canonical/               # canonical reference data (alias -> approved value + code)
│   └── departments.yaml
├── contracts/               # per-dataset data contracts
│   └── orders.yaml
└── soda/                    # compiled quality checks (SodaCL) + Soda data source
    ├── orders.yml
    └── configuration.duckdb.yml
```

## Data contract

A contract (`contracts/<dataset>.yaml`) declares, per field: logical `type`,
`nullable`, an optional `source_name` (raw column), the ordered `cleansing`
rules to apply, and an optional `canonical` map. `quality_gates` list the
value-level checks. See `contracts/orders.yaml`.

## Cleansing rules

Rules are referenced by name from a contract field and implemented in
`../lakehouse/cleansing.py`:

| Rule | Effect | Params |
| --- | --- | --- |
| `trim` | strip + collapse whitespace | — |
| `upper` / `lower` | change case | — |
| `title_case` | Title Case words | — |
| `scrub_diacritics` | `José`→`Jose`, `Bjørk`→`Bjork` (NFKD + stroke/ligature folding) | — |
| `utc_iso8601` | parse → convert to UTC (ISO-8601) | `assume_timezone` for naive input |
| `us_number_format` | `1.234,56`→`1234.56` (mixed EU/US) | `source_format: auto\|eu\|us` |

## Canonical mappings

`canonical/departments.yaml` maps raw spellings (any case, incl. non-English) to
the organisation's approved name and 2-letter code. Matching is
case-insensitive and diacritics-insensitive; unmatched values become
`__UNMAPPED__`, which the `department_is_canonical` gate flags.

## Quality gates

Gates are declared in the contract and run three ways from the same definition:

1. **Natively** on Polars (`../lakehouse/quality.py`) — enforced in the pipeline
   and surfaced as a **Dagster asset check**.
2. **Soda** — compiled to SodaCL (`soda/orders.yml`) via
   `python -m lakehouse.cli sodacl orders`; run with Soda Core/Cloud.
3. **Great Expectations** — supported alternative; map each gate to an
   expectation (`expect_column_values_to_not_be_null`, `_to_be_unique`,
   `_to_be_between`, `_to_be_in_set`, `expect_table_row_count_to_be_between`).

Supported checks: `not_null`, `unique`, `range` (`min`/`max`), `allowed_values`
(explicit `values` or `from_canonical`), and `row_count`.

## Add a dataset

1. Add `canonical/<map>.yaml` if new reference data is needed.
2. Write `contracts/<dataset>.yaml` (fields + cleansing + quality gates).
3. Run `python -m lakehouse.cli run <dataset> <raw_path>`.
4. Regenerate Soda checks: `python -m lakehouse.cli sodacl <dataset> --out governance/soda/<dataset>.yml`.
