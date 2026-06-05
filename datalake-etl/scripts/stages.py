"""Medallion pipeline stages shared by CLI runner and Prefect flows."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.env import lake_root, partition_date
from scripts.metrics import StageResult, count_parquet_rows, observe_stage
from scripts.run_bronze import run_bronze
from scripts.run_gx import run_gx
from scripts.dbt_runner import pipeline_env, run_dbt
from scripts.seed_fixtures import write_fixture

ROOT = Path(__file__).resolve().parents[1]


def _lake_glob(lake_root_value: str, entity_path: str, ds: str) -> str:
    return f"{lake_root_value.rstrip('/')}/{entity_path}/dt={ds}/*.parquet"


def stage_fixtures(*, lake_root_value: str | None = None, ds: str | None = None) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("fixtures", "staging") as result:
        write_fixture(lake_root_value, ds)
        result.row_counts["orders"] = count_parquet_rows(
            f"{lake_root_value.rstrip('/')}/staging/orders/{ds}/*.parquet"
        )
    return result


def stage_ingest(*, lake_root_value: str | None = None, ds: str | None = None) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("ingest", "staging") as result:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "ingest" / "orders_api.py"),
                "--ds",
                ds,
                "--lake-root",
                lake_root_value,
            ],
            check=True,
            env=pipeline_env(),
        )
        result.row_counts["orders"] = count_parquet_rows(
            f"{lake_root_value.rstrip('/')}/staging/orders/{ds}/*.parquet"
        )
    return result


def stage_bronze(*, lake_root_value: str | None = None, ds: str | None = None) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("bronze", "bronze") as result:
        run_bronze(lake_root_value=lake_root_value, ds=ds)
        result.row_counts["orders"] = count_parquet_rows(_lake_glob(lake_root_value, "bronze/orders", ds))
    return result


def stage_gx_bronze(*, lake_root_value: str | None = None, ds: str | None = None) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("gx", "bronze") as result:
        run_gx("bronze", lake_root_value=lake_root_value, ds=ds)
        result.row_counts["orders"] = count_parquet_rows(_lake_glob(lake_root_value, "bronze/orders", ds))
    return result


def stage_silver(*, lake_root_value: str | None = None, ds: str | None = None) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("silver", "silver") as result:
        run_dbt("run", ds, lake_root_value, select="silver.*")
        result.row_counts["orders"] = count_parquet_rows(_lake_glob(lake_root_value, "silver/orders", ds))
        result.row_counts["customers"] = count_parquet_rows(
            _lake_glob(lake_root_value, "silver/customers", ds)
        )
    return result


def stage_gx_silver(*, lake_root_value: str | None = None, ds: str | None = None) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("gx", "silver") as result:
        run_gx("silver", lake_root_value=lake_root_value, ds=ds)
        result.row_counts["orders"] = count_parquet_rows(_lake_glob(lake_root_value, "silver/orders", ds))
    return result


def stage_gold_dimensional(
    *, lake_root_value: str | None = None, ds: str | None = None
) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("gold_dimensional", "gold") as result:
        run_dbt("run", ds, lake_root_value, select="tag:dimensional")
        result.row_counts["dim_customer"] = count_parquet_rows(
            _lake_glob(lake_root_value, "gold/dimensional/dim_customer", ds)
        )
        result.row_counts["fct_orders"] = count_parquet_rows(
            _lake_glob(lake_root_value, "gold/dimensional/fct_orders", ds)
        )
    return result


def stage_gold_denormalized(
    *, lake_root_value: str | None = None, ds: str | None = None
) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("gold_denormalized", "gold") as result:
        run_dbt("run", ds, lake_root_value, select="tag:denormalized")
        result.row_counts["mart_orders_wide"] = count_parquet_rows(
            _lake_glob(lake_root_value, "gold/denormalized/mart_orders_wide", ds)
        )
        result.row_counts["mart_revenue_daily"] = count_parquet_rows(
            _lake_glob(lake_root_value, "gold/denormalized/mart_revenue_daily", ds)
        )
    return result


def stage_test(*, lake_root_value: str | None = None, ds: str | None = None) -> StageResult:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    with observe_stage("test", "quality") as result:
        subprocess.run(
            [sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q"],
            check=True,
            env=pipeline_env(),
        )
        run_dbt("test", ds, lake_root_value)
    return result


def run_all_stages(*, lake_root_value: str | None = None, ds: str | None = None) -> list[StageResult]:
    lake_root_value = lake_root_value or lake_root()
    ds = ds or partition_date()
    runners = (
        stage_fixtures,
        stage_ingest,
        stage_bronze,
        stage_gx_bronze,
        stage_silver,
        stage_gx_silver,
        stage_gold_dimensional,
        stage_gold_denormalized,
        stage_test,
    )
    return [runner(lake_root_value=lake_root_value, ds=ds) for runner in runners]
