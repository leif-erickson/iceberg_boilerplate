"""Medallion pipeline stages as plain functions.

These are engine-agnostic building blocks used by both the Dagster assets and
the CLI/tests:

    raw (bronze) --cleanse+canonicalise--> silver --validate+gate--> Iceberg (gold)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from lakehouse import cleansing, iceberg_io, metrics, quality, settings, validation
from lakehouse.lineage import lineage_run
from lakehouse.registry import DataContract, load_contract


@dataclass
class RunResult:
    dataset: str
    ds: str
    bronze_rows: int
    silver_rows: int
    gold_rows: int
    quality: quality.QualityReport


def read_raw(path: str | Path) -> pl.DataFrame:
    """Read raw input as all-string columns (bronze is source-faithful)."""
    return pl.read_csv(path, infer_schema_length=0)


def build_silver(raw: pl.DataFrame, contract: DataContract) -> pl.DataFrame:
    """Cleanse + canonicalise + schema-validate the raw frame."""
    cleansed = cleansing.apply_contract(raw, contract)
    return validation.validate_schema(cleansed, contract)


def run_dataset(dataset: str, raw_path: str | Path, ds: str | None = None) -> RunResult:
    """Full bronze -> silver -> gold run for one dataset with metrics + lineage."""
    contract = load_contract(dataset)
    ds = ds or settings.partition_date()

    with lineage_run(f"{dataset}.bronze", inputs=[str(raw_path)], outputs=[f"bronze.{dataset}"]):
        with metrics.observe_stage("bronze", "bronze"):
            raw = read_raw(raw_path)
            metrics.record_rows("bronze", "bronze", dataset, raw.height)

    with lineage_run(f"{dataset}.silver", inputs=[f"bronze.{dataset}"], outputs=[f"silver.{dataset}"]):
        with metrics.observe_stage("silver", "silver"):
            silver = build_silver(raw, contract)
            report = quality.run_quality_gates(silver, contract)
            metrics.record_rows("silver", "silver", dataset, silver.height)
            metrics.record_quality(
                dataset,
                passed=len(report.results) - len(report.failures),
                failed=len(report.failures),
            )
            if not report.passed:
                failed = ", ".join(f"{r.name}({r.detail})" for r in report.failures)
                raise quality.QualityGateError(f"{dataset} quality gates failed: {failed}")

    with lineage_run(f"{dataset}.gold", inputs=[f"silver.{dataset}"], outputs=[f"iceberg.{dataset}"]):
        with metrics.observe_stage("gold", "gold"):
            gold_rows = iceberg_io.write_partition(silver, contract, ds)
            metrics.record_rows("gold", "gold", dataset, gold_rows)

    metrics.push_metrics_if_configured()
    return RunResult(dataset, ds, raw.height, silver.height, gold_rows, report)
