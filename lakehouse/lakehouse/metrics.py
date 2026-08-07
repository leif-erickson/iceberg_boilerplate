"""Prometheus metrics for the lakehouse pipeline and quality gates."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import CollectorRegistry, Gauge, Histogram, push_to_gateway, start_http_server

REGISTRY = CollectorRegistry()

STAGE_DURATION_SECONDS = Histogram(
    "lakehouse_stage_duration_seconds",
    "Wall-clock seconds per pipeline stage",
    ["stage", "layer"],
    registry=REGISTRY,
)

STAGE_ROWS = Gauge(
    "lakehouse_stage_rows",
    "Row count observed after a stage completes",
    ["stage", "layer", "dataset"],
    registry=REGISTRY,
)

STAGE_LAST_SUCCESS = Gauge(
    "lakehouse_stage_last_success",
    "1 if the most recent stage run succeeded, else 0",
    ["stage", "layer"],
    registry=REGISTRY,
)

QUALITY_CHECKS_TOTAL = Gauge(
    "lakehouse_quality_checks_total",
    "Number of quality checks by result for the last run",
    ["dataset", "result"],
    registry=REGISTRY,
)

QUALITY_GATE_PASS = Gauge(
    "lakehouse_quality_gate_pass",
    "1 if all quality gates passed for the dataset, else 0",
    ["dataset"],
    registry=REGISTRY,
)


def record_rows(stage: str, layer: str, dataset: str, rows: int) -> None:
    STAGE_ROWS.labels(stage=stage, layer=layer, dataset=dataset).set(rows)


def record_quality(dataset: str, *, passed: int, failed: int) -> None:
    QUALITY_CHECKS_TOTAL.labels(dataset=dataset, result="passed").set(passed)
    QUALITY_CHECKS_TOTAL.labels(dataset=dataset, result="failed").set(failed)
    QUALITY_GATE_PASS.labels(dataset=dataset).set(1 if failed == 0 else 0)


@contextmanager
def observe_stage(stage: str, layer: str) -> Iterator[None]:
    started = time.perf_counter()
    success = True
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        STAGE_DURATION_SECONDS.labels(stage=stage, layer=layer).observe(
            time.perf_counter() - started
        )
        STAGE_LAST_SUCCESS.labels(stage=stage, layer=layer).set(1 if success else 0)


def _enabled() -> bool:
    return os.environ.get("METRICS_DISABLED", "").lower() != "true"


def start_metrics_server_if_configured() -> None:
    port = os.environ.get("METRICS_PORT")
    if port and _enabled():
        start_http_server(int(port), registry=REGISTRY)


def push_metrics_if_configured() -> None:
    gateway = os.environ.get("PROMETHEUS_PUSHGATEWAY_URL")
    if not gateway or not _enabled():
        return
    try:
        push_to_gateway(
            gateway,
            job=os.environ.get("PROMETHEUS_JOB", "lakehouse"),
            grouping_key={"ds": os.environ.get("DS", "unknown")},
            registry=REGISTRY,
        )
    except OSError:
        # Pushgateway is optional locally; never fail the pipeline if it is down.
        pass
