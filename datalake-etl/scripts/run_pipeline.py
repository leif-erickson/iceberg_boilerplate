"""Orchestrate medallion layers with one entrypoint (local and ECS)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from scripts.env import duckdb_path, lake_root, partition_date
from scripts.run_bronze import run_bronze
from scripts.seed_fixtures import write_fixture

ROOT = Path(__file__).resolve().parents[1]


def pipeline_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("DBT_PROFILES_DIR", str(ROOT / "dbt"))
    env.setdefault("DBT_DUCKDB_PATH", str(duckdb_path()))
    return env


def _dbt_executable() -> str:
    local_dbt = Path.home() / ".local" / "bin" / "dbt"
    return str(local_dbt) if local_dbt.exists() else "dbt"


def run_dbt(step: str, ds: str, lake_root_value: str, *, select: str | None = None) -> None:
    cmd = [
        _dbt_executable(),
        step,
        "--project-dir",
        str(ROOT / "dbt"),
        "--profiles-dir",
        str(ROOT / "dbt"),
        "--vars",
        f'{{"ds": "{ds}", "lake_root": "{lake_root_value}"}}',
    ]
    if select:
        cmd.extend(["--select", select])
    subprocess.run(cmd, check=True, env=pipeline_env())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run medallion ETL pipeline")
    parser.add_argument(
        "stage",
        choices=["fixtures", "ingest", "bronze", "silver", "gold", "test", "all"],
        nargs="?",
        default="all",
    )
    parser.add_argument("--lake-root", default=lake_root())
    parser.add_argument("--ds", default=partition_date())
    args = parser.parse_args()

    if args.stage in {"fixtures", "all"}:
        write_fixture(args.lake_root, args.ds)

    if args.stage in {"ingest", "all"}:
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "ingest" / "orders_api.py"),
                "--ds",
                args.ds,
                "--lake-root",
                args.lake_root,
            ],
            check=True,
            env=pipeline_env(),
        )

    if args.stage in {"bronze", "all"}:
        run_bronze(lake_root_value=args.lake_root, ds=args.ds)

    if args.stage in {"silver", "all"}:
        run_dbt("run", args.ds, args.lake_root, select="silver.*")

    if args.stage in {"gold", "all"}:
        run_dbt("run", args.ds, args.lake_root, select="gold.*")

    if args.stage in {"test", "all"}:
        subprocess.run(
            [sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q"],
            check=True,
            env=pipeline_env(),
        )
        run_dbt("test", args.ds, args.lake_root)

    print(f"Pipeline stage '{args.stage}' completed for ds={args.ds}")


if __name__ == "__main__":
    main()
