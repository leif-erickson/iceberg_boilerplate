"""Prefect orchestration for the DuckDB medallion pipeline."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prefect import flow, get_run_logger, task

from scripts.metrics import (
    metrics_enabled,
    push_metrics_if_configured,
    record_pipeline_success,
    start_metrics_server_if_configured,
)
from scripts.stages import (
    StageResult,
    stage_bronze,
    stage_fixtures,
    stage_gold_denormalized,
    stage_gold_dimensional,
    stage_gx_bronze,
    stage_gx_silver,
    stage_ingest,
    stage_silver,
    stage_test,
)


def _task_result(result: StageResult) -> dict[str, Any]:
    return {
        "stage": result.stage,
        "layer": result.layer,
        "duration_seconds": result.duration_seconds,
        "row_counts": result.row_counts,
        "success": result.success,
    }


@task(name="fixtures", retries=1, retry_delay_seconds=10)
def fixtures_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_fixtures(lake_root_value=lake_root_value, ds=ds))


@task(name="ingest", retries=2, retry_delay_seconds=20)
def ingest_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_ingest(lake_root_value=lake_root_value, ds=ds))


@task(name="bronze", retries=2, retry_delay_seconds=30)
def bronze_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_bronze(lake_root_value=lake_root_value, ds=ds))


@task(name="gx-bronze", retries=1, retry_delay_seconds=10)
def gx_bronze_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_gx_bronze(lake_root_value=lake_root_value, ds=ds))


@task(name="silver", retries=2, retry_delay_seconds=30)
def silver_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_silver(lake_root_value=lake_root_value, ds=ds))


@task(name="gx-silver", retries=1, retry_delay_seconds=10)
def gx_silver_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_gx_silver(lake_root_value=lake_root_value, ds=ds))


@task(name="gold-dimensional", retries=2, retry_delay_seconds=30)
def gold_dimensional_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_gold_dimensional(lake_root_value=lake_root_value, ds=ds))


@task(name="gold-denormalized", retries=2, retry_delay_seconds=30)
def gold_denormalized_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_gold_denormalized(lake_root_value=lake_root_value, ds=ds))


@task(name="test", retries=0)
def test_task(lake_root_value: str, ds: str) -> dict[str, Any]:
    return _task_result(stage_test(lake_root_value=lake_root_value, ds=ds))


@flow(name="medallion-etl", log_prints=True)
def medallion_flow(
    lake_root_value: str | None = None,
    ds: str | None = None,
) -> list[dict[str, Any]]:
    """Run the full medallion pipeline with Prefect task boundaries."""
    logger = get_run_logger()
    lake_root_value = lake_root_value or os.environ.get("LAKE_ROOT", "./lake")
    ds = ds or os.environ.get("DS", "2026-06-05")
    os.environ.setdefault("LAKE_ROOT", lake_root_value)
    os.environ.setdefault("DS", ds)

    if metrics_enabled():
        start_metrics_server_if_configured()

    started = time.perf_counter()
    success = False
    results: list[dict[str, Any]] = []
    try:
        results.append(fixtures_task(lake_root_value, ds))
        results.append(ingest_task(lake_root_value, ds))
        results.append(bronze_task(lake_root_value, ds))
        results.append(gx_bronze_task(lake_root_value, ds))
        results.append(silver_task(lake_root_value, ds))
        results.append(gx_silver_task(lake_root_value, ds))
        results.append(gold_dimensional_task(lake_root_value, ds))
        results.append(gold_denormalized_task(lake_root_value, ds))
        results.append(test_task(lake_root_value, ds))
        success = True
        logger.info("Medallion flow completed for ds=%s", ds)
        return results
    finally:
        duration = time.perf_counter() - started
        if metrics_enabled():
            record_pipeline_success("medallion-etl", duration_seconds=duration, success=success)
            push_metrics_if_configured()


if __name__ == "__main__":
    medallion_flow()
