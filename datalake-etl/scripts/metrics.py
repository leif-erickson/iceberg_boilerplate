"""Prometheus metrics for medallion ETL stages."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

import duckdb
from prometheus_client import CollectorRegistry, Gauge, Histogram, push_to_gateway, start_http_server

REGISTRY = CollectorRegistry()

STAGE_DURATION_SECONDS = Histogram(
    "etl_stage_duration_seconds",
    "Wall-clock seconds per pipeline stage",
    ["stage", "layer"],
    registry=REGISTRY,
)

STAGE_ROWS = Gauge(
    "etl_stage_rows",
    "Row count observed after a stage completes",
    ["stage", "layer", "entity"],
    registry=REGISTRY,
)

STAGE_LAST_SUCCESS = Gauge(
    "etl_stage_last_success",
    "1 if the most recent stage run succeeded, else 0",
    ["stage", "layer"],
    registry=REGISTRY,
)

PIPELINE_LAST_SUCCESS = Gauge(
    "etl_pipeline_last_success",
    "1 if the most recent full pipeline run succeeded, else 0",
    ["pipeline"],
    registry=REGISTRY,
)

PIPELINE_DURATION_SECONDS = Histogram(
    "etl_pipeline_duration_seconds",
    "Wall-clock seconds for a full pipeline run",
    ["pipeline"],
    registry=REGISTRY,
)


@dataclass
class StageResult:
    stage: str
    layer: str
    duration_seconds: float = 0.0
    row_counts: dict[str, int] = field(default_factory=dict)
    success: bool = True


def count_parquet_rows(glob_path: str) -> int:
    con = duckdb.connect()
    try:
        row = con.execute(
            f"SELECT count(*) FROM read_parquet('{glob_path}', union_by_name = true)"
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        con.close()


def record_row_counts(result: StageResult) -> None:
    for entity, count in result.row_counts.items():
        STAGE_ROWS.labels(stage=result.stage, layer=result.layer, entity=entity).set(count)


def record_stage_result(result: StageResult) -> None:
    STAGE_DURATION_SECONDS.labels(stage=result.stage, layer=result.layer).observe(
        result.duration_seconds
    )
    STAGE_LAST_SUCCESS.labels(stage=result.stage, layer=result.layer).set(
        1 if result.success else 0
    )
    record_row_counts(result)


@contextmanager
def observe_stage(stage: str, layer: str) -> Iterator[StageResult]:
    started = time.perf_counter()
    result = StageResult(stage=stage, layer=layer)
    try:
        yield result
        result.success = True
    except Exception:
        result.success = False
        raise
    finally:
        result.duration_seconds = time.perf_counter() - started
        record_stage_result(result)


def metrics_enabled() -> bool:
    return os.environ.get("METRICS_DISABLED", "").lower() != "true"


def start_metrics_server_if_configured() -> None:
    port = os.environ.get("METRICS_PORT")
    if port and metrics_enabled():
        start_http_server(int(port), registry=REGISTRY)


def push_metrics_if_configured() -> None:
    gateway = os.environ.get("PROMETHEUS_PUSHGATEWAY_URL")
    if not gateway or not metrics_enabled():
        return
    try:
        push_to_gateway(
            gateway,
            job=os.environ.get("PROMETHEUS_JOB", "medallion_etl"),
            grouping_key={"ds": os.environ.get("DS", "unknown")},
            registry=REGISTRY,
        )
    except OSError:
        # Pushgateway is optional locally; do not fail the pipeline if it is down.
        pass


def record_pipeline_success(pipeline: str, *, duration_seconds: float, success: bool) -> None:
    PIPELINE_DURATION_SECONDS.labels(pipeline=pipeline).observe(duration_seconds)
    PIPELINE_LAST_SUCCESS.labels(pipeline=pipeline).set(1 if success else 0)
