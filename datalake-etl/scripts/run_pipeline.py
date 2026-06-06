"""Orchestrate medallion layers with one entrypoint (local and ECS)."""

from __future__ import annotations

import argparse
import time

from scripts.env import lake_root, partition_date
from scripts.metrics import (
    metrics_enabled,
    push_metrics_if_configured,
    record_pipeline_success,
    start_metrics_server_if_configured,
)
from scripts.stages import (
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

STAGE_MAP = {
    "fixtures": stage_fixtures,
    "ingest": stage_ingest,
    "bronze": stage_bronze,
    "gx-bronze": stage_gx_bronze,
    "silver": stage_silver,
    "gx-silver": stage_gx_silver,
    "gold-dimensional": stage_gold_dimensional,
    "gold-denormalized": stage_gold_denormalized,
    "test": stage_test,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run medallion ETL pipeline")
    parser.add_argument(
        "stage",
        choices=[*STAGE_MAP.keys(), "gold", "all"],
        nargs="?",
        default="all",
    )
    parser.add_argument("--lake-root", default=lake_root())
    parser.add_argument("--ds", default=partition_date())
    args = parser.parse_args()

    if metrics_enabled():
        start_metrics_server_if_configured()

    started = time.perf_counter()
    success = False
    try:
        if args.stage == "all":
            for name in (
                "fixtures",
                "ingest",
                "bronze",
                "gx-bronze",
                "silver",
                "gx-silver",
                "gold-dimensional",
                "gold-denormalized",
                "test",
            ):
                STAGE_MAP[name](lake_root_value=args.lake_root, ds=args.ds)
        elif args.stage == "gold":
            stage_gold_dimensional(lake_root_value=args.lake_root, ds=args.ds)
            stage_gold_denormalized(lake_root_value=args.lake_root, ds=args.ds)
        else:
            STAGE_MAP[args.stage](lake_root_value=args.lake_root, ds=args.ds)
        success = True
        print(f"Pipeline stage '{args.stage}' completed for ds={args.ds}")
    finally:
        if metrics_enabled():
            record_pipeline_success(
                "medallion-cli",
                duration_seconds=time.perf_counter() - started,
                success=success,
            )
            push_metrics_if_configured()


if __name__ == "__main__":
    main()
