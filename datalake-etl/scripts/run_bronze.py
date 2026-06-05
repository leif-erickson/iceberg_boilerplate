"""Run all bronze landing SQL scripts for a partition date."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.env import lake_root, partition_date
from scripts.run_sql import run_sql_file

BRONZE_SQL_DIR = Path(__file__).resolve().parents[1] / "sql" / "bronze"


def run_bronze(*, lake_root_value: str, ds: str) -> None:
    sql_files = sorted(BRONZE_SQL_DIR.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"No bronze SQL files in {BRONZE_SQL_DIR}")

    for sql_file in sql_files:
        run_sql_file(sql_file, lake_root_value=lake_root_value, ds=ds)
        print(f"Bronze landed: {sql_file.name} -> ds={ds}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Land staging data into bronze Parquet")
    parser.add_argument("--lake-root", default=lake_root())
    parser.add_argument("--ds", default=partition_date())
    args = parser.parse_args()
    run_bronze(lake_root_value=args.lake_root, ds=args.ds)


if __name__ == "__main__":
    main()
