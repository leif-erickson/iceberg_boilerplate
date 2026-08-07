"""Dagster assets + asset checks for the governance-driven medallion pipeline.

Assets are thin wrappers over `lakehouse.pipeline` so the same logic runs from
Dagster, the CLI, and tests. The contract's quality gates surface as native
Dagster asset checks, and Prometheus metrics + OpenLineage events are emitted
per stage.
"""

import os

import polars as pl
from dagster import (
    AssetCheckResult,
    AssetCheckSeverity,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    asset,
    asset_check,
)

from lakehouse import iceberg_io, metrics, quality, settings
from lakehouse.lineage import lineage_run
from lakehouse.pipeline import build_silver, read_raw
from lakehouse.registry import load_contract

DATASET = "orders"


def _raw_path() -> str:
    return os.environ.get("ORDERS_RAW", str(settings.PROJECT_ROOT / "data" / "raw" / "orders.csv"))


@asset(group_name="orders", description="Raw orders landed source-faithful (bronze).")
def bronze_orders() -> pl.DataFrame:
    with lineage_run(f"{DATASET}.bronze", inputs=[_raw_path()], outputs=[f"bronze.{DATASET}"]):
        with metrics.observe_stage("bronze", "bronze"):
            frame = read_raw(_raw_path())
            metrics.record_rows("bronze", "bronze", DATASET, frame.height)
    return frame


@asset(group_name="orders", description="Cleansed + canonicalised + schema-validated (silver).")
def silver_orders(context: AssetExecutionContext, bronze_orders: pl.DataFrame) -> pl.DataFrame:
    contract = load_contract(DATASET)
    with lineage_run(f"{DATASET}.silver", inputs=[f"bronze.{DATASET}"], outputs=[f"silver.{DATASET}"]):
        with metrics.observe_stage("silver", "silver"):
            frame = build_silver(bronze_orders, contract)
            metrics.record_rows("silver", "silver", DATASET, frame.height)
    context.add_output_metadata(
        {
            "rows": frame.height,
            "columns": MetadataValue.text(", ".join(frame.columns)),
            "preview": MetadataValue.md(f"```\n{frame.head(5)}\n```"),
        }
    )
    return frame


@asset_check(asset=silver_orders, description="Run the contract's declarative quality gates.")
def orders_quality_gates(silver_orders: pl.DataFrame) -> AssetCheckResult:
    contract = load_contract(DATASET)
    report = quality.run_quality_gates(silver_orders, contract)
    metrics.record_quality(
        DATASET,
        passed=len(report.results) - len(report.failures),
        failed=len(report.failures),
    )
    return AssetCheckResult(
        passed=report.passed,
        severity=AssetCheckSeverity.ERROR,
        metadata={r.name: f"{'PASS' if r.passed else 'FAIL'} {r.detail}".strip() for r in report.results},
    )


@asset(group_name="orders", description="Published Iceberg table partitioned by dt (gold).")
def orders_iceberg(silver_orders: pl.DataFrame) -> MaterializeResult:
    contract = load_contract(DATASET)
    ds = settings.partition_date()
    with lineage_run(f"{DATASET}.gold", inputs=[f"silver.{DATASET}"], outputs=[f"iceberg.{DATASET}"]):
        with metrics.observe_stage("gold", "gold"):
            rows = iceberg_io.write_partition(silver_orders, contract, ds)
            metrics.record_rows("gold", "gold", DATASET, rows)
    metrics.push_metrics_if_configured()
    table = f"{settings.catalog_namespace()}.{contract.dataset}"
    return MaterializeResult(metadata={"rows": rows, "iceberg_table": table, "partition": f"dt={ds}"})
