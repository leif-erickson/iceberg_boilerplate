"""Run Great Expectations checkpoints against lake Parquet via DuckDB."""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from quality.suites.bronze_orders import validate as validate_bronze_orders
from quality.suites.silver_orders import validate as validate_silver_orders
from scripts.env import lake_root, partition_date
from scripts.lineage import lineage_run

ROOT = Path(__file__).resolve().parents[1]


def _read_lake_df(glob_path: str):
    con = duckdb.connect()
    try:
        return con.execute(
            f"SELECT * FROM read_parquet('{glob_path}', union_by_name = true)"
        ).df()
    finally:
        con.close()


def run_gx(layer: str, *, lake_root_value: str, ds: str) -> None:
    if layer == "bronze":
        glob_path = f"{lake_root_value.rstrip('/')}/bronze/orders/dt={ds}/*.parquet"
        job = "quality.bronze.orders"
        inputs = [f"bronze/orders/dt={ds}"]
        outputs = inputs
        validate_fn = validate_bronze_orders
    elif layer == "silver":
        glob_path = f"{lake_root_value.rstrip('/')}/silver/orders/dt={ds}/*.parquet"
        job = "quality.silver.orders"
        inputs = [f"silver/orders/dt={ds}"]
        outputs = inputs
        validate_fn = validate_silver_orders
    else:
        raise ValueError(f"Unknown GX layer: {layer}")

    with lineage_run(job, inputs=inputs, outputs=outputs):
        df = _read_lake_df(glob_path)
        validate_fn(df)
    print(f"GX passed: {layer}.orders ds={ds}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Great Expectations on lake partitions")
    parser.add_argument("layer", choices=["bronze", "silver", "all"])
    parser.add_argument("--lake-root", default=lake_root())
    parser.add_argument("--ds", default=partition_date())
    args = parser.parse_args()

    layers = ["bronze", "silver"] if args.layer == "all" else [args.layer]
    for layer in layers:
        run_gx(layer, lake_root_value=args.lake_root, ds=args.ds)


if __name__ == "__main__":
    main()
